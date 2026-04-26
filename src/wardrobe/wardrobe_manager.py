"""
Wardrobe Manager: persists garment metadata as a JSON database and manages photo files.
"""

import json
import shutil
import uuid
from pathlib import Path

from .analyzer import GarmentAnalyzer


class WardrobeManager:
    def __init__(self, data_dir: str = "data/wardrobe_db"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir = self.data_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "wardrobe.json"
        self._db: dict = self._load_db()
        self.analyzer = GarmentAnalyzer()

    def _load_db(self) -> dict:
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_db(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._db, f, ensure_ascii=False, indent=2)

    def add_garment(self, image_path: str, custom_name: str | None = None) -> dict:
        """
        Add a garment to the wardrobe: copy photo, run AI analysis, persist metadata.
        Returns the full garment record.
        """
        garment_id = str(uuid.uuid4())[:8]
        src = Path(image_path)
        dest = self.photos_dir / f"{garment_id}{src.suffix}"
        shutil.copy2(src, dest)

        metadata = self.analyzer.analyze(str(src))
        metadata["id"] = garment_id
        metadata["photo_path"] = str(dest)
        metadata["name"] = custom_name or metadata.get("description", garment_id)

        self._db[garment_id] = metadata
        self._save_db()
        return metadata

    def remove_garment(self, garment_id: str) -> bool:
        if garment_id not in self._db:
            return False
        photo = Path(self._db[garment_id]["photo_path"])
        if photo.exists():
            photo.unlink()
        del self._db[garment_id]
        self._save_db()
        return True

    def get_all(self) -> list[dict]:
        return list(self._db.values())

    def get_by_id(self, garment_id: str) -> dict | None:
        return self._db.get(garment_id)

    def get_by_category(self, category: str) -> list[dict]:
        return [g for g in self._db.values() if g.get("category") == category]

    def summary(self) -> dict:
        """Return a compact summary suitable for LLM prompts."""
        items = []
        for g in self._db.values():
            items.append({
                "id": g["id"],
                "name": g["name"],
                "category": g["category"],
                "subcategory": g.get("subcategory", ""),
                "colors": g.get("colors", {}),
                "style_tags": g.get("style_tags", []),
                "fit": g.get("fit", ""),
                "notable_details": g.get("notable_details", ""),
                "season": g.get("season", []),
                "formality": g.get("formality", "casual"),
            })
        return {"total": len(items), "items": items}
