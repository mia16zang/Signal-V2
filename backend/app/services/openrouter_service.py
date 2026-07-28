import os
import re
import json
import time
import requests

from dotenv import load_dotenv

load_dotenv()


class OpenRouterService:

    def __init__(self):

        self.api_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        self.url = (
            "https://openrouter.ai/api/v1/chat/completions"
        )

        self.default_model = (
            "openrouter/free"
        )

    def call(
        self,
        prompt,
        model=None,
        debug=False
    ):

        model = (
            model
            or
            self.default_model
        )

        print(
            "\nMODEL:",
            model
        )

        headers = {

            "Authorization":
            f"Bearer {self.api_key}",

            "Content-Type":
            "application/json",

            "HTTP-Referer":
            "http://localhost",

            "X-Title":
            "Signal"
        }

        payload = {

            "model":
            model,

            "messages": [

                {
                    "role":
                    "system",

                    "content":
                    (
                        "You are a JSON API. "
                        "Return only valid JSON. "
                        "Do not explain. "
                        "Do not use markdown. "
                        "Do not wrap JSON in code fences."
                    )
                },

                {
                    "role":
                    "user",

                    "content":
                    prompt
                }
            ]
        }

        response = None

        for attempt in range(3):

            response = requests.post(

                self.url,

                timeout=90,

                headers=headers,

                json=payload
            )

            if response.status_code == 429:

                wait_time = (
                    5 * (attempt + 1)
                )

                print(
                    f"\nOPENROUTER RATE LIMITED "
                    f"(attempt {attempt + 1}/3). "
                    f"Retrying in {wait_time}s..."
                )

                time.sleep(
                    wait_time
                )

                continue

            break

        if debug:

            print(
                "\nOPENROUTER STATUS:",
                response.status_code
            )

            print(
                "\nOPENROUTER BODY:\n",
                response.text[:5000]
            )

        response.raise_for_status()

        data = response.json()

        return (
            data["choices"][0]
            ["message"]
            ["content"]
        )

    def call_json(
        self,
        prompt,
        model=None,
        debug=False
    ):

        response_text = self.call(
            prompt=prompt,
            model=model,
            debug=debug
        )

        print(
            "\nRAW RESPONSE:\n"
        )

        print(
            response_text[:5000]
        )

        try:

            parsed = json.loads(
                response_text
            )

            print(
                "\nJSON PARSE SUCCESS"
            )

            return parsed

        except Exception:

            pass

        match = re.search(
            r"\{.*\}",
            response_text,
            re.DOTALL
        )

        if not match:

            print(
                "\nNO JSON FOUND IN RESPONSE\n"
            )

            return {

                "error":
                "no_json",

                "raw_response":
                response_text
            }

        candidate = match.group()

        try:

            parsed = json.loads(
                candidate
            )

            print(
                "\nREGEX JSON PARSE SUCCESS"
            )

            return parsed

        except Exception as e:

            print(
                "\nINVALID JSON FROM MODEL:\n"
            )

            print(
                candidate[:5000]
            )

            print(
                "\nJSON ERROR:\n",
                str(e)
            )

            return {

                "error":
                "invalid_json",

                "raw_response":
                candidate
            }