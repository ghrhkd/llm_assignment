"""
Virtual Try-On Pipeline: orchestrates sequential layering of multiple garments.

Strategy for multi-garment outfits:
  1. Apply bottom (trousers/skirt) first on the original person photo.
  2. Apply inner upper layer (t-shirt, shirt, knitwear) on top.
  3. Apply outer layer (jacket, coat) last.
  4. Shoes are appended as a side-by-side panel (try-on models rarely handle footwear well).

Each step feeds its output as the new "person" image for the next step.
"""

import os
import tempfile
from pathlib import Path

from PIL import Image

from .backends import get_backend

# Map garment categories/subcategories to model category tokens
CATEGORY_MAP = {
    "bottom": "lower_body",
    "top": "upper_body",
    "outerwear": "upper_body",
    "shoes": "skip",        # handled separately
    "accessory": "skip",
}

LAYER_ORDER = ["bottom", "top", "outerwear"]


def _category_token(garment: dict) -> str:
    cat = garment.get("category", "top").lower()
    return CATEGORY_MAP.get(cat, "upper_body")


def _save_pil_temp(img: Image.Image, suffix: str = ".jpg") -> str:
    """Save PIL image to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    img.save(tmp.name, format="JPEG", quality=95)
    return tmp.name


class TryOnPipeline:
    def __init__(self, backend_name: str | None = None):
        backend_name = backend_name or os.environ.get("TRYON_BACKEND", "replicate")
        self.backend = get_backend(backend_name)
        self.output_dir = Path("data/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_single(
        self,
        person_img_path: str,
        garment: dict,
    ) -> Image.Image:
        """Try on a single garment. Returns PIL Image."""
        token = _category_token(garment)
        if token == "skip":
            return Image.open(person_img_path).convert("RGB")

        desc = garment.get("description", garment.get("name", ""))
        return self.backend.tryon(
            person_img_path=person_img_path,
            garment_img_path=garment["photo_path"],
            garment_description=desc,
            category=token,
        )

    def run_outfit(
        self,
        person_img_path: str,
        outfit_items: list[dict],
        outfit_title: str = "outfit",
    ) -> Image.Image:
        """
        Try on a full outfit (multiple garments) sequentially.
        outfit_items: list of garment dicts (with photo_path, category, etc.)
        Returns the final composite PIL Image.
        """
        # Sort by layer order
        def sort_key(g):
            cat = g.get("category", "top").lower()
            return LAYER_ORDER.index(cat) if cat in LAYER_ORDER else 99

        sorted_garments = sorted(outfit_items, key=sort_key)
        skipped = [g for g in sorted_garments if _category_token(g) == "skip"]
        to_apply = [g for g in sorted_garments if _category_token(g) != "skip"]

        current_path = person_img_path
        temp_files = []

        try:
            for garment in to_apply:
                result_img = self.run_single(current_path, garment)
                tmp_path = _save_pil_temp(result_img)
                temp_files.append(tmp_path)
                current_path = tmp_path

            final_img = Image.open(current_path).convert("RGB")

            # Append skipped items (shoes/accessories) as a small panel on the right
            if skipped:
                final_img = self._append_item_panel(final_img, skipped)

        finally:
            for tf in temp_files:
                try:
                    os.unlink(tf)
                except OSError:
                    pass

        # Save output
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in outfit_title)
        out_path = self.output_dir / f"{safe_title.replace(' ', '_')}.jpg"
        final_img.save(out_path, format="JPEG", quality=95)
        return final_img

    def _append_item_panel(self, main_img: Image.Image, items: list[dict]) -> Image.Image:
        """
        Creates a side panel showing skipped items (shoes, accessories)
        and appends it to the right of the main try-on image.
        """
        panel_w = 160
        padding = 8
        item_h = (main_img.height - padding * (len(items) + 1)) // len(items)
        item_h = max(item_h, 80)

        panel = Image.new("RGB", (panel_w, main_img.height), color=(245, 245, 245))

        y = padding
        for item in items:
            try:
                thumb = Image.open(item["photo_path"]).convert("RGB")
                thumb.thumbnail((panel_w - padding * 2, item_h))
                panel.paste(thumb, (padding, y))
                y += item_h + padding
            except (OSError, KeyError):
                continue

        combined = Image.new("RGB", (main_img.width + panel_w, main_img.height), (245, 245, 245))
        combined.paste(main_img, (0, 0))
        combined.paste(panel, (main_img.width, 0))
        return combined
