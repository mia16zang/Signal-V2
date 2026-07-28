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

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app import config
from app.services.json_utils import parse_json

load_dotenv()


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
                print(
                    f"  gemini {model} failed after {elapsed:.1f}s "
                    f"(attempt {attempt}/{config.LLM_MAX_ATTEMPTS}): "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                if attempt < config.LLM_MAX_ATTEMPTS:
                    time.sleep(1.5 * attempt)

        raise RuntimeError(f"gemini call failed: {last_error}")

    def call_json(self, prompt, model=None):
        return parse_json(self.call(prompt, model=model, json_mode=True))
