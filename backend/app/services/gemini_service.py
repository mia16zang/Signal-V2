"""Gemini client.

Two changes carry all the speed:

  thinking_budget=0    gemini-2.5-flash reasons before answering by default.
                       The old synthesis call measured 16.9-38.7s (median
                       25.5s) across 14 production runs with it enabled.
                       Extraction against supplied evidence does not need a
                       reasoning pass.

  response_mime_type   Constrains decoding to JSON, so the "model wrapped it
                       in prose" failure mode stops happening at the source.
                       The recovery path in json_utils is still there.
"""

import logging
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app import config
from app.services.json_utils import parse_json

load_dotenv()

log = logging.getLogger("signal.gemini")


class LLMUnavailable(RuntimeError):
    """The provider returned nothing usable. Distinct from a bad reply.

    Worth its own type because the two failures need opposite handling: a bad
    reply can be parsed, repaired or retried, while no reply at all means there
    is no briefing to serve and the request should say so.
    """

    def __init__(self, message, retryable=False, retry_after=None):
        super().__init__(message)
        self.retryable = retryable
        # Seconds until a retry would plausibly succeed, when the provider
        # supplied a figure. None when it did not.
        self.retry_after = retry_after


# Conditions that do not fix themselves inside one request. Retrying these
# burns the user's wall-clock for nothing -- measured 4.5s of sleeps across
# three attempts against a quota that resets daily.
_FATAL_MARKERS = (
    "INVALID_ARGUMENT", "PERMISSION_DENIED", "UNAUTHENTICATED",
    "NOT_FOUND", "API key not valid", "400", "401", "403", "404",
)

_RETRY_DELAY = re.compile(r"['\"]retryDelay['\"]:\s*['\"](\d+(?:\.\d+)?)s['\"]")

# Gemini names the exact quota that was violated, and its numeric limit, in the
# error details. Truncating the error before this point -- which the first
# version of this file did at 200 chars -- throws away the only part that says
# *which* ceiling was hit and how high it is.
_QUOTA_ID = re.compile(r"['\"]quotaId['\"]:\s*['\"]([^'\"]+)['\"]")
_QUOTA_METRIC = re.compile(r"['\"]quotaMetric['\"]:\s*['\"]([^'\"]+)['\"]")
_QUOTA_VALUE = re.compile(r"['\"]quotaValue['\"]:\s*['\"]?(\d+)")


def _suggested_delay(error) -> float | None:
    """The server's own advice on when to try again, if it gave any."""
    match = _RETRY_DELAY.search(str(error))
    return float(match.group(1)) if match else None


def quota_detail(error) -> str:
    """Which limit was hit, and what it is set to."""
    text = str(error)
    parts = []
    for label, pattern in (("quota", _QUOTA_ID), ("metric", _QUOTA_METRIC),
                           ("limit", _QUOTA_VALUE)):
        match = pattern.search(text)
        if match:
            parts.append(f"{label}={match.group(1)}")
    delay = _suggested_delay(error)
    if delay is not None:
        parts.append(f"retryDelay={delay}s")
    return " ".join(parts) or "no quota detail supplied"


def classify(error) -> tuple[bool, float | None, str]:
    """(retryable, wait_seconds, reason)."""
    text = str(error)

    if any(marker in text for marker in _FATAL_MARKERS):
        return False, None, "request rejected by the provider"

    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        delay = _suggested_delay(error)

        # Measured on the free tier, 2026-08-02:
        #   quotaId    GenerateRequestsPerMinutePerProjectPerModel-FreeTier
        #   quotaValue 5
        #   retryDelay 33s
        #
        # So the ceiling that actually bites is 5 requests per *minute* per
        # model, not a daily allowance -- and it clears on its own. Calling it
        # "quota exhausted" was wrong in the same way the rest of this session
        # has been about: a default message standing in for a fact nobody
        # checked.
        if delay is None:
            return False, None, "rate limited, no retry window supplied"

        if delay <= config.LLM_MAX_RETRY_WAIT_SECONDS:
            return True, delay, f"rate limited, clears in {delay:.0f}s"

        # Waitable in principle, but not inside a request that already costs
        # ~30s. Fail fast and hand the caller the retry window instead.
        return False, delay, f"rate limited, clears in {delay:.0f}s"

    return True, None, "transient provider error"


class GeminiService:

    _client = None

    @classmethod
    def client(cls):
        # One client for the process. The old code built a fresh genai.Client
        # on every call, which re-read credentials and rebuilt the transport.
        if cls._client is None:
            cls._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        return cls._client

    def _config(self, json_mode: bool):
        return types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=config.LLM_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json" if json_mode else "text/plain",
            thinking_config=types.ThinkingConfig(
                thinking_budget=config.GEMINI_THINKING_BUDGET
            ),
            http_options=types.HttpOptions(
                timeout=config.LLM_TIMEOUT_SECONDS * 1000
            ),
        )

    def call(self, prompt, model=None, json_mode=True):
        model = model or config.GEMINI_MODEL

        last_error = None

        for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
            started = time.time()
            try:
                response = self.client().models.generate_content(
                    model=model,
                    contents=prompt,
                    config=self._config(json_mode),
                )
                elapsed = time.time() - started
                print(f"  gemini {model} ok in {elapsed:.1f}s (attempt {attempt})")
                return response.text or ""

            except Exception as e:
                last_error = e
                elapsed = time.time() - started
                retryable, wait, reason = classify(e)

                print(
                    f"  gemini {model} failed after {elapsed:.1f}s "
                    f"(attempt {attempt}/{config.LLM_MAX_ATTEMPTS}, {reason}): "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )

                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    # Full, untruncated: this is the line that answers "how
                    # many requests a day can this take?".
                    log.warning("gemini quota hit | %s | full=%s",
                                quota_detail(e), str(e))

                if not retryable:
                    log.warning("gemini call not retryable | reason=%s error=%s",
                                reason, str(e)[:200])
                    unavailable = LLMUnavailable(
                        f"gemini call failed ({reason}): {str(e)[:200]}",
                        retryable=False,
                    )
                    # Seconds until this would succeed, when the provider said.
                    unavailable.retry_after = wait
                    raise unavailable from e

                if attempt < config.LLM_MAX_ATTEMPTS:
                    time.sleep(wait if wait is not None else 1.5 * attempt)

        log.warning("gemini exhausted %d attempts | error=%s",
                    config.LLM_MAX_ATTEMPTS, str(last_error)[:200])
        raise LLMUnavailable(f"gemini call failed: {last_error}", retryable=True)

    def call_json(self, prompt, model=None):
        return parse_json(self.call(prompt, model=model, json_mode=True))
