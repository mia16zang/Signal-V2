import os
import json
import re

from google import genai
from dotenv import load_dotenv

load_dotenv()


class GeminiService:

    def __init__(self):

        self.client = genai.Client(
            api_key=os.getenv(
                "GEMINI_API_KEY"
            )
        )

    def call(
        self,
        prompt,
        model="gemini-2.5-flash"
    ):

        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )

        return response.text

    def call_json(
        self,
        prompt,
        model="gemini-2.5-flash"
    ):

        response_text = self.call(
            prompt=prompt,
            model=model
        )

        try:

            return json.loads(
                response_text
            )

        except Exception:

            match = re.search(
                r"\{.*\}",
                response_text,
                re.DOTALL
            )

            if not match:

                print(
                    "\nRAW GEMINI RESPONSE:"
                )

                print(
                    response_text
                )

                return {
                    "error":
                    "no_json",

                    "raw_response":
                    response_text
                }

            return json.loads(
                match.group()
            )