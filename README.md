# Clothing Matching Workflow — Setup Guide

Complete setup guide for running the **Clothing Matching Workflow** (`Clothing Matching Workflow.json`) in ComfyUI.

## Workflow Overview

This workflow performs **two-stage full-body virtual try-on with face swap**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Clothing Matching Pipeline                    │
│                                                                 │
│  Stage 1: Upper Body Try-On                                     │
│  ┌──────────┐   ┌────────────┐   ┌──────────┐                  │
│  │ Human    │──▶│ DWPose     │──▶│ Pose Img │                  │
│  │ Image    │   │ Estimator  │   │          │                  │
│  └──────────┘   └────────────┘   └────┬─────┘                  │
│  ┌──────────┐   ┌────────────┐        │                        │
│  │ Garment  │   │SAM + DINO  │        ▼                        │
│  │ (Jacket) │──▶│(seg "jacket")├──▶ IDM-VTON ──▶ Upper Result │
│  └──────────┘   └────────────┘                                 │
│                                                                 │
│  Stage 2: Lower Body Try-On                                    │
│  ┌──────────┐   ┌────────────┐                                │
│  │ Garment  │   │SAM + DINO  │                                │
│  │ (Pants)  │──▶│(seg "pants")├──▶ IDM-VTON ──▶ Full Body     │
│  └──────────┘   └────────────┘       (uses Upper as human)      │
│                                                                 │
│  Stage 3: Face Swap                                            │
│  Full Body + Source Face ──▶ ReActor ──▶ Final Output          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Nodes Used in This Workflow

| # | Node | `class_type` | Custom Node Package | Purpose |
|---|------|-------------|---------------------|---------|
| 2, 4, 22, 50 | Load Image | `LoadImage` | Built-in | Input images |
| 3 | DWPose Estimator | `DWPreprocessor` | **comfyui_controlnet_aux** | Extract human pose skeleton |
| 5, 16 | SAM Loader | `SAMModelLoader (segment anything)` | **comfyui_segment_anything** | Load SAM segmentation model |
| 6, 17 | GroundingDINO Loader | `GroundingDinoModelLoader (segment anything)` | **comfyui_segment_anything** | Load text-prompted object detector |
| 7, 18 | Segment | `GroundingDinoSAMSegment (segment anything)` | **comfyui_segment_anything** | Segment garment region by text prompt |
| 9, 25 | Mask to Image | `MaskToImage` | Built-in | Convert mask to image format |
| 1, 23 | Try-On | `IDM-VTON` | **ComfyUI-IDM-VTON** | Core virtual try-on generation |
| 10, 24 | Pipeline Loader | `PipelineLoader` | **ComfyUI-IDM-VTON** | Load IDM-VTON model pipeline |
| 29 | Face Swap | `ReActorFaceSwap` | **ComfyUI-ReActor** | Face replacement |
| 31 | Save Output | `SaveImage` | Built-in | Save final result |

---

## Prerequisites

- **ComfyUI** installed: [github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- **Python 3.10+** with PyTorch (CUDA recommended)
- **~40 GB free disk space** for all models
- **~20 GB VRAM** GPU memory recommended

---

## Step 0: Install ComfyUI

### Option A: Clone from GitHub (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/comfyanonymous/ComfyUI.git

# 2. Enter the directory
cd ComfyUI

# 3. Create a Python virtual environment (strongly recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 4. Install Python dependencies
pip install -r requirements.txt
```

### Option B: Use ComfyUI Portable (Windows, Easiest)

Download the pre-packaged portable version — no Python or Git required:

- **Download**: [ComfyUI_windows_portable](https://github.com/comfyanonymous/ComfyUI/releases/latest)
- Extract and run `run_nvidia_gpu.bat` (NVIDIA GPU) or `run_cpu.bat` (CPU-only)

> The portable version includes its own embedded Python environment.

### Option C: Docker / RunPod / Cloud GPU (For cloud users)

Many cloud GPU providers offer **one-click ComfyUI deployment**:

| Provider | How to Launch |
|----------|--------------|
| **RunPod** | Community Cloud → Template → `comfyanonymous/ComfyUI` |
| **Vast.ai** | Search "ComfyUI" in templates |
| **Google Colab** | Search "ComfyUI Colab notebook" on GitHub |

### Option D: Pinokio (One-click desktop app)

[Pinokio](https://pinokio.computer/) is a browser that lets you install and run ComfyUI with a single click:

```bash
# 1. Download & install Pinokio from https://pinokio.computer/
# 2. Open Pinokio → search "ComfyUI"
# 3. Click install → it handles everything automatically
```

### Verify Installation

```bash
# Start ComfyUI
cd ComfyUI
source venv/bin/activate   # if using venv
python main.py
```

Open your browser to `http://127.0.0.1:8188` — you should see the ComfyUI interface.

**Default ports:**
- Web UI: `http://127.0.0.1:8188`
- API: `http://127.0.0.1:8188/prompt`
- Input folder: `ComfyUI/input/`
- Output folder: `ComfyUI/output/`

> **Tip**: To access ComfyUI from another machine (e.g., remote server), launch with:
> ```bash
> python main.py --listen 0.0.0.0 --port 8188
> ```

---

## Step 1: Install Custom Nodes

Run these commands inside your `ComfyUI/custom_nodes/` directory:

```bash
cd /path/to/ComfyUI/custom_nodes/

# 1. IDM-VTON (Core try-on pipeline — REQUIRED)
git clone https://github.com/Kosinkadink/ComfyUI-IDM-VTON.git

# 2. ControlNet Aux (DWPose pose estimation — REQUIRED)
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git

# 3. SAM + GroundingDINO (Text-guided image segmentation — REQUIRED)
git clone https://github.com/storyicon/comfyui_segment_anything.git

# 4. ReActor (Face swap — REQUIRED for this workflow)
git clone https://github.com/artgantry/ComfyUI-ReActor.git
```

### Node Installation Summary

| # | Custom Node | Git URL | Required For |
|---|------------|---------|--------------|
| 1 | **ComfyUI-IDM-VTON** | `Kosinkadink/ComfyUI-IDM-VTON` | `IDM-VTON`, `PipelineLoader` nodes |
| 2 | **comfyui_controlnet_aux** | `Fannovel16/comfyui_controlnet_aux` | `DWPreprocessor` node |
| 3 | **comfyui_segment_anything** | `storyicon/comfyui_segment_anything` | `SAMModelLoader`, `GroundingDinoModelLoader`, `GroundingDinoSAMSegment` nodes |
| 4 | **ComfyUI-ReActor** | `artgantry/ComfyUI-ReActor` | `ReActorFaceSwap` node |

> After cloning all nodes, **restart ComfyUI** so they are loaded.

---

## Step 2: Download Models

All models should be placed under your ComfyUI models directory.
The default path is `ComfyUI/models/`, or configure via `extra_model_paths.yaml`.

### 2A. IDM-VTON Pipeline Models (~28 GB total)

Download from [HuggingFace: IDM-VTON/IDM-VTON-comfyui-native](https://huggingface.co/IDM-VTON/IDM-VTON-comfyui-native):

```
models/
└── IDM-VTON/
    ├── unet/
    │   └── diffusion_pytorch_model.bin              (12.0 GB) ⬅ SDXL UNet
    ├── unet_encoder/
    │   └── diffusion_pytorch_model.safetensors       (9.6 GB)  ⬅ Garment Encoder UNet
    ├── text_encoder/
    │   └── model.safetensors                         (470 MB)  ⬅ CLIP Text Encoder
    ├── text_encoder_2/
    │   └── model.safetensors                         (2.6 GB)  ⬅ CLIP Text Encoder 2 (SDXL)
    ├── image_encoder/
    │   └── model.safetensors                         (2.4 GB)  ⬅ CLIP Vision Encoder
    ├── vae/
    │   └── diffusion_pytorch_model.safetensors       (320 MB)  ⬅ VAE
    ├── openpose/
    │   └── ckpts/body_pose_model.pth                 (200 MB)  ⬅ OpenPose body keypoints
    ├── humanparsing/
    │   ├── parsing_atr.onnx                          (255 MB)  ⬅ Attribute parsing
    │   └── parsing_lip.onnx                          (255 MB)  ⬅ LIP part segmentation
    ├── densepose/
    │   └── ...                                       (244 MB)  ⬅ DensePose (optional)
    └── assets/
        └── ...                                       (16 MB)   ⬅ Config files
```

**One-command download (HuggingFace CLI):**
```bash
# Install huggingface-hub first
pip install huggingface_hub

# Download entire repo
huggingface-cli download IDM-VTON/IDM-VTON-comfyui-native \
    --local-dir ./models/IDM-VTON
```

### 2B. SAM Model (~2.57 GB)

Used by the **GroundingDinoSAMSegment** node for text-prompted clothing segmentation.

```
models/
└── sams/
    └── sam_hq_vit_h.pth                              (2.57 GB)
```

**Download:**
```bash
# Auto-downloaded by comfyui_segment_anything on first use,
# OR download manually:
wget -O models/sams/sam_hq_vit_h.pth \
    "https://dl.fbaipublicfiles.com/segment_anything/sam_hq_vit_h.pth"
```

> The workflow uses model name: `sam_hq_vit_h (2.57GB)` in node 5 and 16.

### 2C. GroundingDINO Model (~938 MB)

Used together with SAM for text-guided object detection ("jacket", "pants").

```
models/
└── grounding-dino/
    └── groundingdino_swinb_cogcoor.pth               (938 MB)
```

**Download:**
```bash
# Auto-downloaded on first use, OR:
wget -O models/grounding-dino/groundingdino_swinb_cogcoor.pth \
    "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha2/groundingdino_swinb_cogcoor.pth"
```

> The workflow uses model name: `GroundingDINO_SwinB (938MB)` in node 6 and 17.

### 2D. InsightFace Models (for ReActor face swap)

```
models/
├── insightface/
│   └── inswapper_128.onnx                            (528 MB)  ⬅ Face swap core model
└── facedetection/
    ├── yolov5l-face.pth                               (~140 MB) ⬅ Face detection (RetinaNet)
    └── detection_Resnet50_Final.pth                   (~170 MB) ⬅ Alternative detector
```

**Download inswapper:**
```bash
mkdir -p models/insightface
# From the original insightface model zoo:
# Or from ComfyUI-ReActor's wiki:
wget -O models/insightface/inswapper_128.onnx \
    "https://huggingface.co/deepinsight/inswapper_pytorch/resolve/main/inswapper_128.onnx"
```

**Download buffalo_l (auto-downloaded):**
```bash
# This is auto-downloaded by insightface library on first use into:
# models/insightface/models/buffalo_l/
python -c "import insightface; insightface.model_zoo.download_model('buffalo_l', root='models/insightface')"
```

> Files created: `det_10g.onnx`, `w600k_r50.onnx`, `2d106det.onnx`, `genderage.onnx`, `1k3d68.onnx`

### 2E. Face Restoration Models (for ReActor post-processing)

```
models/
└── facerestore_models/
    ├── codeformer-v0.1.0.pth                           (~350 MB) ⬅ CodeFormer restoration
    └── GFPGANv1.4.pth                                  (332 MB)  ⬅ GFPGAN restoration
```

The workflow uses **CodeFormer** (`codeformer-v0.1.0.pth`) as the face restore model.

**Download:**
```bash
mkdir -p models/facerestore_models
wget -O models/facerestore_models/codeformer-v0.1.0.pth \
    "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer-v0.1.0.pth"

wget -O models/facerestore_models/GFPGANv1.4.pth \
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
```

### 2F. DWPose Models (auto-downloaded)

The `DWPreprocessor` node downloads its own models automatically on first use:
- `yolox_l.onnx` — body bounding box detection
- `dw-ll_ucoco_384_bs5.torchscript.pt` — pose keypoint estimation

These go into ComfyUI's internal model cache (not your models directory).

---

## Step 3: Configure Model Paths (if needed)

If you store models in a non-default location, edit `extra_model_paths.yaml`:

```yaml
# extra_model_paths.yaml (place next to main.py)
comfyui-meta:
    base_path: /path/to/my_models
    is_default: true
    IDM-VTON: IDM-VTON
    insightface: insightface
    facerestore_models: facerestore_models
    facedetection: facedetection
    sams: sams
    grounding-dino: grounding-dino
```

Then restart ComfyUI.

---

## Complete Download Script

Save as `download_models.sh` and run:

```bash
#!/usr/bin/env bash
set -e

MODELS_DIR="${1:-./models}"
mkdir -p "$MODELS_DIR"/{IDM-VTON/{unet,unet_encoder,text_encoder,text_encoder_2,image_encoder,vae,openpose,humanparsing,densepose,assets},\
                insightface/models/buffalo_l,\
                facerestore_models,facedetection,sams,grounding-dino}

echo "=== [1/6] Downloading IDM-VTON Pipeline (~28 GB) ==="
huggingface-cli download IDM-VTON/IDM-VTON-comfyui-native --local-dir "$MODELS_DIR/IDM-VTON"

echo ""
echo "=== [2/6] Downloading SAM HQ (~2.57 GB) ==="
[ -f "$MODELS_DIR/sams/sam_hq_vit_h.pth" ] || \
    wget -O "$MODELS_DIR/sams/sam_hq_vit_h.pth" \
    "https://dl.fbaipublicfiles.com/segment_anything/sam_hq_vit_h.pth"

echo ""
echo "=== [3/6] Downloading GroundingDINO (~938 MB) ==="
[ -f "$MODELS_DIR/grounding-dino/groundingdino_swinb_cogcoor.pth" ] || \
    wget -O "$MODELS_DIR/grounding-dino/groundingdino_swinb_cogcoor.pth" \
    "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha2/groundingdino_swinb_cogcoor.pth"

echo ""
echo "=== [4/6] Downloading inswapper_128 face swap model (~528 MB) ==="
[ -f "$MODELS_DIR/insightface/inswapper_128.onnx" ] || \
    wget -O "$MODELS_DIR/insightface/inswagger_128.onnx" \
    "https://huggingface.co/deepinsight/inswapper_pytorch/resolve/main/inswapper_128.onnx"

echo ""
echo "=== [5/6] Downloading CodeFormer face restoration (~350 MB) ==="
[ -f "$MODELS_DIR/facerestore_models/codeformer-v0.1.0.pth" ] || \
    wget -O "$MODELS_DIR/facerestore_models/codeformer-v0.1.0.pth" \
    "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer-v0.1.0.pth"

echo ""
echo "=== [6/6] Downloading GFPGAN face restoration (~332 MB) ==="
[ -f "$MODELS_DIR/facerestore_models/GFPGANv1.4.pth" ] || \
    wget -O "$MODELS_DIR/facerestore_models/GFPGANv1.4.pth" \
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"

echo ""
echo "=== Downloading InsightFace buffalo_l (ArcFace) ==="
pip install insightface -q
python -c "
import insightface
insightface.model_zoo.download_model('buffalo_l', root='$MODELS_DIR/insightface')
"

echo ""
echo "✅ All models downloaded to: $MODELS_DIR/"
echo ""
echo "Model sizes:"
du -sh "$MODELS_DIR"/*/
```

---

## How to Run

1. **Place input images** in `ComfyUI/input/`:
   - Human/model body image (e.g., `微信图片_20260503182930.png`)
   - Upper garment image (e.g., `thisisneverthat_jk001_15.jpg`) — white background preferred
   - Lower garment image (e.g., `thisisneverthat_bottom_xxx.jpg`)
   - Source face image (e.g., `微信图片_20260503175508.png`)

2. **Open ComfyUI** → Menu → **Load** → Select `Clothing Matching Workflow.json`

3. **Update image filenames** in the `LoadImage` nodes if your files have different names:
   - Node 2: Human image
   - Node 4: Upper garment (jacket/coat)
   - Node 22: Lower garment (pants)
   - Node 50: Source face reference

4. **Adjust parameters** (optional):
   - Node 1 / 23 (`IDM-VTON`):
     - `garment_description`: Describe the garment (e.g., "a camouflage zip-up jacket")
     - `faceid_weight`: 0.0–2.0 (how strongly to preserve face identity, default 1.2/0.8)
     - `strength`: 0.0–1.0 (how much to change, default 0.6/0.8)
     - `num_inference_steps`: 30 (more steps = better quality but slower)
   - Node 29 (`ReActorFaceSwap`):
     - `swap_model`: `inswapper_128.onnx`
     - `face_restore_model`: `codeformer-v0.1.0.pth`
     - `codeformer_weight`: 0–1 (0=none, 1=full restoration)

5. Click **Queue Prompt** and wait for output.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `class_type not found` for any of the custom nodes | Make sure the corresponding `custom_nodes/` package is cloned and ComfyUI has been restarted |
| `FileNotFoundError` for IDM-VTON models | Verify all subfolders exist under `models/IDM-VTON/`. Total size should be ~28 GB. Use HuggingFace CLI to download |
| SAM model not found | Ensure `sam_hq_vit_h.pth` exists in `models/sams/` (or wherever `sams` path points to) |
| GroundingDINO model not found | Ensure `groundingdino_swinb_cogcoor.pth` is in `models/grounding-dino/` |
| ReActor: `inswapper_128.onnx` not found | Place it in `models/insightface/` |
| Out of VRAM (CUDA OOM) | Set `weight_dtype` to `float16` (default) in PipelineLoader nodes. If still OOM, reduce batch size or use CPU offload |
| DWPose fails on first run | It auto-downloads models; just retry after the download completes |
| Face swap looks unnatural | Increase `codeformer_weight` in ReActor node, or switch to `GFPGANv1.4.pth` |

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 12 GB (FP16) | 20 GB+ (for full pipeline without offloading) |
| System RAM | 32 GB | 64 GB |
| Disk Space | 45 GB (all models) | 60 GB+ (with room for outputs) |
| GPU Memory Type | CUDA | CUDA 11.8+ / ROCm 5.4+ |

---

## Architecture Notes

### Why This Two-Stage Approach?

Single-stage full-body virtual try-on often produces artifacts where upper and lower garments interact at the waist. This workflow splits the process:

1. **Stage 1 (Upper)**: Focuses only on the torso/jacket area using a precise "jacket" text prompt for SAM segmentation
2. **Stage 2 (Lower)**: Takes the upper-body result as the new "human" input, then tries on pants using a "pants" segmentation mask
3. **Stage 3 (Face)**: Applies face swap as post-processing since IDM-VTON's built-in FaceID may not fully preserve identity

### Known Limitations & Future Improvements

| Current Limitation | Proposed Solution |
|---------------------|------------------|
| ReActor produces visible seam artifacts around face edges | Replace with **PuLID Flux** workflow (`flux_pulid_tryon.json`) which injects face features during diffusion |
| Two-stage approach can cause inconsistencies at waist junction | Use **Flux.1 inpainting** with full-body mask instead of sequential processing |
| SDXL-based IDM-VTON has quality ceiling | Upgrade to **Flux.1 Dev** ecosystem (see `comfyui/workflows/flux_pulid_tryon.json`) |

See the companion README at [`comfyui/README.md`](../yhg/comfyui/README.md) for the upgraded Flux + PuLID workflow.
