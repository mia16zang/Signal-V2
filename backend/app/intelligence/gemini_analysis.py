import os
import json
from dotenv import load_dotenv


from google import genai

load_dotenv()
async def analyze_with_gemini(
    evidence
):

    client = genai.Client(
        api_key=os.getenv(
            "GEMINI_API_KEY"
        )
    )

    evidence_text = "\n".join(

        f"{e['title']} - {e['snippet']}"

        for e in evidence[:20]
    )

    prompt = f"""
You are a market intelligence analyst.

Analyze this evidence.

{evidence_text}

Return ONLY valid JSON.

{{
  "market_pulse": {{
    "growth": 0,
    "competition": 0,
    "virality": 0,
    "sentiment": 0,
    "funding": 0,
    "pricing_power": 0
  }},
  "opportunities": [],
  "threats": []
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return json.loads(
        response.text
    )