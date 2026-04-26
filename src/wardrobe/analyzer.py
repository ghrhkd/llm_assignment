"""
Garment Analyzer: uses GPT-4o Vision to extract structured metadata from clothing photos.
"""

import base64
import json
import os
import re
from pathlib import Path

from openai import OpenAI

ANALYSIS_PROMPT = """
You are a professional fashion stylist with deep expertise in streetwear, vintage, and contemporary fashion.
Analyze this clothing item and return a JSON object with the following structure:

{
  "category": "one of: top/outerwear/bottom/shoes/accessory",
  "subcategory": "e.g. t-shirt/hoodie/jacket/trousers/sneakers/cap",
  "colors": {
    "primary": "main color name",
    "secondary": ["additional color names if any"]
  },
  "style_tags": ["e.g. streetwear, vintage, military, minimalist, techwear, cityboy"],
  "material": "fabric or material description",
  "fit": "one of: oversized/regular/slim/baggy/cropped",
  "season": ["suitable seasons: spring/summer/autumn/winter"],
  "notable_details": "distinctive features like logos, embroidery, patterns, hardware",
  "description": "one concise sentence describing this item",
  "formality": "one of: casual/smart-casual/formal",
  "gender": "one of: menswear/womenswear/unisex"
}

Be specific and accurate. If the image is unclear, make your best inference.
Return ONLY valid JSON, no additional text.
"""


class GarmentAnalyzer:
    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze(self, image_path: str) -> dict:
        """Analyze a single garment image and return structured metadata."""
        b64 = self._encode_image(image_path)
        ext = Path(image_path).suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
            max_tokens=600,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if model wraps output
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
