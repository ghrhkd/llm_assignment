import os
import glob
import pandas as pd
import torch
import pyiqa
from tqdm import tqdm

def evaluate_images(image_dir, output_csv="quality_scores.csv"):
    # 1. Set device (GPU accelerates evaluation significantly)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Current compute device: {device}")

    # 2. Initialize evaluation models
    print("Loading MUSIQ and NIQE models...")
    # as_loss=False means we want scores, not loss values
    musiq_metric = pyiqa.create_metric('musiq', device=device, as_loss=False)
    niqe_metric = pyiqa.create_metric('niqe', device=device, as_loss=False)

    # 3. Collect all image paths (supports jpg, png, jpeg)
    valid_extensions = ('*.jpg', '*.jpeg', '*.png')
    image_paths = []
    for ext in valid_extensions:
        image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
    
    if not image_paths:
        print(f"ERROR: No images found in {image_dir}!")
        return

    print(f"Found {len(image_paths)} images, starting evaluation...")

    # 4. Iterate through images and compute scores
    results = []
    # Use tqdm for a nice progress bar
    for img_path in tqdm(image_paths, desc="Evaluating"):
        filename = os.path.basename(img_path)
        
        try:
            # Disable gradient computation to save VRAM
            with torch.no_grad():
                # pyiqa handles tensor conversion automatically given a file path
                musiq_score = musiq_metric(img_path).item()
                niqe_score = niqe_metric(img_path).item()
                
            results.append({
                "Filename": filename,
                "MUSIQ_Score": musiq_score,
                "NIQE_Score": niqe_score
            })
        except Exception as e:
            print(f"Error processing image {filename}: {e}")

    # 5. Save results to CSV and sort
    df = pd.DataFrame(results)

    # Sort by MUSIQ ascending so worst images appear first
    df_sorted = df.sort_values(by="MUSIQ_Score", ascending=True)

    df_sorted.to_csv(output_csv, index=False)
    print(f"\nEvaluation complete! Results saved to: {output_csv}")

    # Print top-5 worst images for manual review
    print("\n--- Top-5 Worst Images Requiring Manual Review (Lowest MUSIQ Scores) ---")
    print(df_sorted.head(5).to_string(index=False))

if __name__ == "__main__":
    # ---> Change this to your generated images folder path <---
    TARGET_IMAGE_FOLDER = "/root/comfyui-meta/output" 
    
    evaluate_images(TARGET_IMAGE_FOLDER)