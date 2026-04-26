"""
Outfit Recommender: uses GPT-4o to generate outfit combinations from wardrobe items.
"""

import json
import os
import re

from openai import OpenAI

SYSTEM_PROMPT = """You are a world-class fashion stylist specializing in streetwear, vintage, Cityboy, techwear,
and contemporary men's fashion. You have deep knowledge of:
- Color theory and harmonious palette combinations
- Style coherence (mixing pieces that share a visual language)
- Layering techniques
- Occasion-appropriate dressing
- Brand aesthetics and subculture codes

Your recommendations should feel curated, intentional, and wearable — not generic.
Always explain the *why* behind each choice."""

RECOMMENDATION_PROMPT = """Here is the user's wardrobe inventory:
{wardrobe_json}

User's request:
- Occasion: {occasion}
- Style preference: {style}
- Weather/Season: {season}
- Additional notes: {notes}

Generate exactly 3 outfit combinations using ONLY items from the wardrobe above (referenced by their "id" field).
Each outfit must include at minimum: a bottom + one upper layer.
Include outerwear and shoes only if available in the wardrobe.

Return a JSON array with this structure:
[
  {{
    "outfit_number": 1,
    "title": "short evocative name for the look",
    "vibe": "one-line mood description",
    "items": [
      {{"id": "garment_id", "role": "e.g. base layer / outer layer / bottom / footwear"}}
    ],
    "styling_notes": "2-3 sentences on how to wear this and why it works",
    "color_story": "brief color palette explanation"
  }}
]

Return ONLY valid JSON, no markdown fences or extra text."""


class OutfitRecommender:
    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])

    def recommend(
        self,
        wardrobe_summary: dict,
        occasion: str = "casual street",
        style: str = "streetwear / Cityboy",
        season: str = "autumn",
        notes: str = "",
    ) -> list[dict]:
        """
        Generate 3 outfit recommendations from wardrobe summary.
        wardrobe_summary should come from WardrobeManager.summary().
        """
        prompt = RECOMMENDATION_PROMPT.format(
            wardrobe_json=json.dumps(wardrobe_summary, ensure_ascii=False, indent=2),
            occasion=occasion,
            style=style,
            season=season,
            notes=notes or "none",
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.8,
        )

        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        outfits = json.loads(raw)

        # Enrich each outfit item with full garment metadata
        id_map = {g["id"]: g for g in wardrobe_summary["items"]}
        for outfit in outfits:
            for item in outfit["items"]:
                item["metadata"] = id_map.get(item["id"], {})

        return outfits

    def explain_outfit(self, outfit: dict) -> str:
        """Generate a detailed styling explanation for a given outfit dict."""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Give a detailed, enthusiastic styling explanation for this outfit:\n"
                        f"{json.dumps(outfit, ensure_ascii=False, indent=2)}\n\n"
                        "Write 3-4 sentences in a conversational, fashion-forward tone. "
                        "Mention specific pieces, textures, and the overall aesthetic."
                    ),
                },
            ],
            max_tokens=300,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
