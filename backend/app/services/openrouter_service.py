"""OpenRouter client.

The important change is the model. The old default was "openrouter/free",
which is a router alias, not a model: each request queues behind whichever
free model the router happens to pick. Across 14 cached production runs the
three intelligence calls took a 34.8s median but 64s, 76s and 126s on three
of them -- a 21% chance of a recruiter watching a two-minute spinner. Pinning
an explicit model removes that tail.

Retry, JSON cleaning and fallback parsing are all preserved; the parsing now
lives in json_utils so Gemini and OpenRouter recover identically.
"""

import os
import time

import requests
from dotenv import load_dotenv

from app import config
from app.services.json_utils import parse_json

load_dotenv()

SYSTEM_PROMPT = (
    "You are a JSON API. Return only valid JSON. Do not explain. "
    "Do not use markdown. Do not wrap JSON in code fences."
)


class OpenRouterService:

    URL = "https://openrouter.ai/api/v1/chat/completions"

    _session = None

    @classmethod
    def session(cls):
        # Reuse the TCP/TLS connection across calls. The old code called
        # requests.post directly, paying a fresh handshake every time.
        if cls._session is None:
            cls._session = requests.Session()
        return cls._session

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    def call(self, prompt, model=None, debug=False):
        model = model or config.OPENROUTER_MODEL

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Signal",
        }

        payload = {
            "model": model,
            "temperature": 0.3,
            "max_tokens": config.LLM_MAX_OUTPUT_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }

        last_error = None

        for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
            started = time.time()
            try:
                response = self.session().post(
                    self.URL,
                    headers=headers,
                    json=payload,
                    timeout=config.LLM_TIMEOUT_SECONDS,
                )
            except requests.RequestException as e:
                last_error = e
                print(
                    f"  openrouter {model} transport error after "
                    f"{time.time() - started:.1f}s (attempt {attempt}): {e}"
                )
                if attempt < config.LLM_MAX_ATTEMPTS:
                    time.sleep(2 * attempt)
                continue

            elapsed = time.time() - started

            if response.status_code == 429:
                wait = 3 * attempt
                print(
                    f"  openrouter rate limited after {elapsed:.1f}s "
                    f"(attempt {attempt}/{config.LLM_MAX_ATTEMPTS}), "
                    f"retrying in {wait}s"
                )
                last_error = RuntimeError("rate limited")
                if attempt < config.LLM_MAX_ATTEMPTS:
                    time.sleep(wait)
                continue

            if debug:
                print("  openrouter status:", response.status_code)
                print("  openrouter body:", response.text[:1000])

            if response.status_code >= 400:
                last_error = RuntimeError(
                    f"{response.status_code}: {response.text[:300]}"
                )
                print(f"  openrouter {model} http {response.status_code}: "
                      f"{response.text[:200]}")
                if attempt < config.LLM_MAX_ATTEMPTS:
                    time.sleep(1.5 * attempt)
                continue

            data = response.json()

            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                last_error = RuntimeError(f"unexpected body: {str(data)[:300]}")
                print(f"  openrouter {model} unexpected body: {str(data)[:200]}")
                continue

            print(f"  openrouter {model} ok in {elapsed:.1f}s (attempt {attempt})")
            return content or ""

        raise RuntimeError(f"openrouter call failed: {last_error}")

    def call_json(self, prompt, model=None, debug=False):
        return parse_json(self.call(prompt, model=model, debug=debug))
