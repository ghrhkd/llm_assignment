"""
Virtual Try-On backends: Replicate (cloud API) and HuggingFace Spaces (free inference).
Both implement the same interface: tryon(person_img_path, garment_img_path, category) -> PIL.Image
"""

import io
import os
import time
from pathlib import Path

import requests
from PIL import Image


# ---------------------------------------------------------------------------
# Replicate backend  (IDM-VTON)
# ---------------------------------------------------------------------------

REPLICATE_MODEL = "cuuupid/idm-vton:c871bb9b046607b680449ecbae55fd8c6d945e0a1948644bf2361b3d021d3ff4"


class ReplicateBackend:
    """
    Uses IDM-VTON on Replicate.  Costs ~$0.05 per call.
    Docs: https://replicate.com/cuuupid/idm-vton
    """

    def __init__(self, api_token: str | None = None):
        self.token = api_token or os.environ["REPLICATE_API_TOKEN"]

    def tryon(
        self,
        person_img_path: str,
        garment_img_path: str,
        garment_description: str = "",
        category: str = "upper_body",
    ) -> Image.Image:
        """
        category: "upper_body" | "lower_body" | "dresses"
        """
        import replicate

        os.environ["REPLICATE_API_TOKEN"] = self.token

        with open(person_img_path, "rb") as pf, open(garment_img_path, "rb") as gf:
            output = replicate.run(
                REPLICATE_MODEL,
                input={
                    "human_img": pf,
                    "garm_img": gf,
                    "garment_des": garment_description,
                    "is_checked": True,
                    "is_checked_crop": False,
                    "denoise_steps": 30,
                    "seed": 42,
                },
            )

        # output is a URL string
        url = output if isinstance(output, str) else list(output)[0]
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")


# ---------------------------------------------------------------------------
# HuggingFace Spaces backend  (OOTDiffusion – free but slower)
# ---------------------------------------------------------------------------

HF_SPACE_URL = "https://levihsu-ootdiffusion.hf.space"


class HuggingFaceBackend:
    """
    Uses the public OOTDiffusion Gradio Space on HuggingFace (free, no API key needed).
    May have queue wait times.
    """

    def tryon(
        self,
        person_img_path: str,
        garment_img_path: str,
        garment_description: str = "",
        category: str = "upper_body",
    ) -> Image.Image:
        try:
            from gradio_client import Client, handle_file
        except ImportError as exc:
            raise ImportError("pip install gradio_client") from exc

        client = Client(HF_SPACE_URL)

        # OOTDiffusion model_type: "Half-body" or "Full-body"
        model_type = "Half-body" if category == "upper_body" else "Full-body"

        result = client.predict(
            vton_img=handle_file(person_img_path),
            garm_img=handle_file(garment_img_path),
            n_samples=1,
            n_steps=20,
            image_scale=2.0,
            seed=-1,
            api_name="/process_hd",
        )

        # result is a list of image file paths
        img_path = result[0] if isinstance(result, list) else result
        return Image.open(img_path).convert("RGB")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_backend(name: str = "replicate"):
    if name == "replicate":
        return ReplicateBackend()
    elif name == "huggingface":
        return HuggingFaceBackend()
    raise ValueError(f"Unknown backend: {name}. Choose 'replicate' or 'huggingface'.")
