import os
import requests
import asyncio
import glob
import hashlib  # Hash library for URL dedup
import re  # Regex module for URL cleaning
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# Global config
OUTPUT_DIR = "dataset_raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def download_image(url: str, save_path: str):
    """Download image using requests and save to disk"""
    try:
        # Add basic headers to bypass simple hotlink protection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  [+] Downloaded: {save_path}")
    except Exception as e:
        print(f"  [-] Download failed {url}: {e}")


async def scrape_product_page(page, product_url: str, sku_id: str):
    """Scrape all high-res images from a single product page (optimized for Shopify architecture)"""
    print(f"Parsing product: {sku_id} - {product_url}")

    sku_dir = os.path.join(OUTPUT_DIR, sku_id)
    os.makedirs(sku_dir, exist_ok=True)

    try:
        # 1. Use domcontentloaded strategy -- start as soon as the page frame is ready
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)

        # 2. Explicitly wait for target images (up to 10s)
        # More reliable than network idle -- as soon as images appear, we start scraping
        await page.wait_for_selector("img[src*='cdn.shopify.com/s/files/']", timeout=10000)

        # [Modification 1: Attribute selector]
        # Match img elements whose src contains Shopify CDN path, avoiding UI icons on the page
        image_elements = await page.locator("img[src*='cdn.shopify.com/s/files/']").all()

        # Also check data-src for lazy-loaded images that might be missed
        # image_elements = await page.locator("img[src*='cdn.shopify.com/s/files/'], img[data-src*='cdn.shopify.com/s/files/']").all()

        download_tasks = []
        img_count = 0
        seen_urls = set()  # For dedup -- detail pages often have duplicate thumbnails pointing to the same full-size image

        existing_files = glob.glob(os.path.join(sku_dir, f"{sku_id}_*.jpg"))
        img_count = 0
        if existing_files:
            # Extract numeric part from filename, find max value
            indices = []
            for f in existing_files:
                match = re.search(r'_(\d+)\.jpg$', f)
                if match:
                    indices.append(int(match.group(1)))
            if indices:
                img_count = max(indices)

        print(f"Detected existing data, resuming from index {img_count + 1}.")
        for img in image_elements:
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if not src:
                continue

            src = urljoin(product_url, src)

            # [Modification 2: Regex-based URL cleaning, extract highest resolution original]
            # Regex explanation: matches _NxM format (e.g., _640x, _1024x1024) followed by image extension
            # Replace with empty string to restore original high-quality Shopify image URL
            high_res_src = re.sub(r'_\d+x\d*(?=\.jpg|\.jpeg|\.png|\.webp)', '', src, flags=re.IGNORECASE)

            # Filter out obvious non-product images and duplicate links
            if "logo" in high_res_src.lower() or high_res_src in seen_urls:
                continue

            seen_urls.add(high_res_src)
            img_count += 1

            url_hash = hashlib.md5(high_res_src.encode('utf-8')).hexdigest()[:10]  # First 10 hex chars suffice for near-zero collision rate
            filename = f"{sku_id}_{url_hash}.jpg"
            save_path = os.path.join(sku_dir, filename)

            # [New]: File dedup logic
            if os.path.exists(save_path):
                print(f"  -> [Skip] Image already exists: {filename}")
                continue  # Skip, don't re-download

            print(f"  -> Found new image: {high_res_src}")
            download_tasks.append(download_image(high_res_src, save_path))

        if download_tasks:
            # Control concurrency to avoid getting IP-banned by Shopify for too many simultaneous requests
            # Uses asyncio.Semaphore for simple concurrency control (optional advanced optimization)
            await asyncio.gather(*download_tasks)
            print(f"Product {sku_id} done, downloaded {len(download_tasks)} ultra-HD images.\n")
        else:
            print(f"No Shopify CDN images found for product {sku_id}, please check page structure.\n")

    except Exception as e:
        print(f"Failed to parse page {product_url}: {e}")


async def main():
    # Test product list (SKU_ID : URL)
    products = {
        # "thisisneverthat_upper": "https://thisisneverthat.com/collections/outerwear",
        "thisisneverthat_bottom": "https://thisisneverthat.com/collections/archive-bottoms",
        # "uniqlo_u_tshirt": "https://www.uniqlo.com/...",
    }

    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        # Create context with preset User-Agent and Viewport
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for sku_id, url in products.items():
            await scrape_product_page(page, url, sku_id)
            # Polite scraping: random sleep to avoid triggering anti-bot measures
            await asyncio.sleep(2)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())