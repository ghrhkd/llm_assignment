"""Entry point: loads .env and launches the Gradio app."""

import os
from dotenv import load_dotenv

load_dotenv()

from src.ui.app import build_app

if __name__ == "__main__":
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=os.environ.get("GRADIO_SHARE", "false").lower() == "true",
        show_error=True,
    )
