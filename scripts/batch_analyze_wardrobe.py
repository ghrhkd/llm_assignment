"""
Batch import a folder of clothing photos into the wardrobe database.

Usage:
    python scripts/batch_analyze_wardrobe.py --folder /path/to/photos

Supported formats: .jpg .jpeg .png .webp
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.wardrobe.wardrobe_manager import WardrobeManager

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser(description="Batch import clothing photos into wardrobe")
    parser.add_argument("--folder", required=True, help="Folder containing clothing photos")
    parser.add_argument("--data-dir", default="data/wardrobe_db", help="Wardrobe database directory")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"[ERROR] Folder not found: {folder}")
        sys.exit(1)

    images = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED]
    if not images:
        print(f"[ERROR] No supported images found in {folder}")
        sys.exit(1)

    print(f"Found {len(images)} images. Starting analysis...\n")
    wm = WardrobeManager(data_dir=args.data_dir)

    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}] Analyzing: {img_path.name}")
        try:
            record = wm.add_garment(str(img_path))
            print(f"  → {record['category']} | {record['colors']['primary']} | {record.get('description', '')}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print(f"\n✅ Done. Wardrobe now has {len(wm.get_all())} items.")
    print(f"   Database saved to: {wm.db_path}")


if __name__ == "__main__":
    main()
