"""
Gradio Web UI for the AI Wardrobe Assistant.

Tabs:
  1. My Wardrobe  – add / view / delete garments
  2. Get Outfits  – request recommendations and try-on renders
  3. Single Try-On – quick single-garment try-on tool
"""

import json
import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Lazy imports so the app can start even if user hasn't set up keys yet
def _get_wardrobe():
    from src.wardrobe.wardrobe_manager import WardrobeManager
    return WardrobeManager()

def _get_recommender():
    from src.recommender.outfit_recommender import OutfitRecommender
    return OutfitRecommender()

def _get_pipeline():
    from src.tryon.pipeline import TryOnPipeline
    return TryOnPipeline()


# ─────────────────────────────────────────────
# Tab 1: Wardrobe Management
# ─────────────────────────────────────────────

def add_garment_fn(image, custom_name):
    if image is None:
        return "请先上传衣服照片。", _load_wardrobe_gallery()
    wm = _get_wardrobe()
    try:
        record = wm.add_garment(image, custom_name.strip() or None)
        summary = (
            f"✅ 添加成功！\n\n"
            f"**类别**: {record.get('category')} / {record.get('subcategory')}\n"
            f"**颜色**: {record.get('colors', {}).get('primary')}\n"
            f"**风格**: {', '.join(record.get('style_tags', []))}\n"
            f"**细节**: {record.get('notable_details')}\n"
            f"**描述**: {record.get('description')}"
        )
        return summary, _load_wardrobe_gallery()
    except Exception as e:
        return f"❌ 出错了: {e}", _load_wardrobe_gallery()


def _load_wardrobe_gallery():
    wm = _get_wardrobe()
    items = wm.get_all()
    return [(item["photo_path"], item.get("name", item["id"])) for item in items if Path(item["photo_path"]).exists()]


def delete_garment_fn(garment_id):
    if not garment_id.strip():
        return "请输入要删除的衣服 ID。", _load_wardrobe_gallery()
    wm = _get_wardrobe()
    ok = wm.remove_garment(garment_id.strip())
    msg = f"✅ 已删除 {garment_id}" if ok else f"❌ 未找到 ID: {garment_id}"
    return msg, _load_wardrobe_gallery()


def refresh_gallery_fn():
    return _load_wardrobe_gallery()


# ─────────────────────────────────────────────
# Tab 2: Outfit Recommendation + Try-On
# ─────────────────────────────────────────────

_current_outfits: list[dict] = []


def recommend_outfits_fn(occasion, style, season, notes):
    global _current_outfits
    wm = _get_wardrobe()
    items = wm.get_all()
    if len(items) < 2:
        return "衣橱里的单品太少了，请先添加至少 2 件衣服。", gr.update(choices=[]), None

    rec = _get_recommender()
    summary = wm.summary()
    try:
        outfits = rec.recommend(summary, occasion, style, season, notes)
        _current_outfits = outfits
    except Exception as e:
        return f"❌ 推荐出错: {e}", gr.update(choices=[]), None

    choices = [f"#{o['outfit_number']} {o['title']}" for o in outfits]
    display = _format_outfits_markdown(outfits)
    return display, gr.update(choices=choices, value=choices[0] if choices else None), None


def _format_outfits_markdown(outfits: list[dict]) -> str:
    lines = []
    for o in outfits:
        lines.append(f"## #{o['outfit_number']} {o['title']}")
        lines.append(f"*{o['vibe']}*\n")
        lines.append("**单品列表:**")
        for item in o["items"]:
            meta = item.get("metadata", {})
            name = meta.get("name") or meta.get("description") or item["id"]
            lines.append(f"- [{item['role']}] {name}  `ID: {item['id']}`")
        lines.append(f"\n**色彩故事:** {o.get('color_story', '')}")
        lines.append(f"\n**造型建议:** {o.get('styling_notes', '')}\n")
        lines.append("---")
    return "\n".join(lines)


def generate_tryon_fn(person_img, outfit_choice, progress=gr.Progress()):
    global _current_outfits
    if person_img is None:
        return None, "请先上传你的照片。"
    if not _current_outfits or not outfit_choice:
        return None, "请先生成搭配方案。"

    # Parse selected outfit number from label like "#1 Cityboy Weekend"
    try:
        outfit_num = int(outfit_choice.split()[0].lstrip("#"))
        outfit = next(o for o in _current_outfits if o["outfit_number"] == outfit_num)
    except (ValueError, StopIteration):
        return None, "无法识别所选套装。"

    wm = _get_wardrobe()
    garment_ids = [item["id"] for item in outfit["items"]]
    garments = [wm.get_by_id(gid) for gid in garment_ids if wm.get_by_id(gid)]

    if not garments:
        return None, "未找到对应单品图片，请检查衣橱数据。"

    pipeline = _get_pipeline()
    try:
        progress(0.1, desc="开始生成上身效果图...")
        result = pipeline.run_outfit(person_img, garments, outfit_title=outfit.get("title", "outfit"))
        progress(1.0, desc="完成！")
        return result, f"✅ 《{outfit['title']}》上身效果图生成完毕！"
    except Exception as e:
        return None, f"❌ 生成失败: {e}"


# ─────────────────────────────────────────────
# Tab 3: Single Try-On (Quick Test)
# ─────────────────────────────────────────────

def single_tryon_fn(person_img, garment_img, description, category):
    if person_img is None or garment_img is None:
        return None, "请上传人物照片和衣服照片。"

    import tempfile, shutil
    from src.tryon.backends import get_backend

    backend_name = os.environ.get("TRYON_BACKEND", "replicate")
    backend = get_backend(backend_name)

    # Save gradio temp paths properly
    try:
        result = backend.tryon(
            person_img_path=person_img,
            garment_img_path=garment_img,
            garment_description=description,
            category=category,
        )
        return result, "✅ 单件试穿完成！"
    except Exception as e:
        return None, f"❌ 试穿失败: {e}"


# ─────────────────────────────────────────────
# Build Gradio App
# ─────────────────────────────────────────────

CSS = """
.gradio-container { max-width: 1200px !important; }
.outfit-card { border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; margin: 8px 0; }
footer { display: none !important; }
"""

THEME = gr.themes.Soft(
    primary_hue="slate",
    secondary_hue="gray",
    neutral_hue="gray",
    font=gr.themes.GoogleFont("Inter"),
)


def build_app() -> gr.Blocks:
    with gr.Blocks(theme=THEME, css=CSS, title="AI 衣橱助手") as demo:

        gr.Markdown(
            """
            # 👔 AI 衣橱助手
            **上传你的衣服 → 获取 AI 搭配推荐 → 生成逼真上身效果图**
            """
        )

        # ── Tab 1: Wardrobe ──────────────────────────────────────
        with gr.Tab("🗄️ 我的衣橱"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 添加新单品")
                    add_img = gr.Image(label="衣服照片", type="filepath", height=280)
                    add_name = gr.Textbox(label="自定义名称（可选）", placeholder="例如：军绿工装夹克")
                    add_btn = gr.Button("📥 添加到衣橱", variant="primary")
                    add_status = gr.Markdown()

                with gr.Column(scale=2):
                    gr.Markdown("### 衣橱一览")
                    wardrobe_gallery = gr.Gallery(
                        label="",
                        columns=4,
                        height=420,
                        object_fit="contain",
                        show_label=False,
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 刷新")
                        del_id_input = gr.Textbox(label="删除单品 ID", scale=2)
                        del_btn = gr.Button("🗑️ 删除", variant="stop", scale=1)
                    del_status = gr.Markdown()

            add_btn.click(
                add_garment_fn,
                inputs=[add_img, add_name],
                outputs=[add_status, wardrobe_gallery],
            )
            refresh_btn.click(refresh_gallery_fn, outputs=[wardrobe_gallery])
            del_btn.click(
                delete_garment_fn,
                inputs=[del_id_input],
                outputs=[del_status, wardrobe_gallery],
            )
            demo.load(refresh_gallery_fn, outputs=[wardrobe_gallery])

        # ── Tab 2: Recommend + Try-On ────────────────────────────
        with gr.Tab("✨ 搭配推荐 & 试穿"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 告诉我你的需求")
                    occasion_input = gr.Textbox(
                        label="场合",
                        placeholder="例如：周末逛街 / 下午约会 / 通勤上班",
                        value="周末街头",
                    )
                    style_input = gr.Textbox(
                        label="风格偏好",
                        placeholder="例如：Cityboy / 机能风 / 复古街头",
                        value="Cityboy 街头",
                    )
                    season_input = gr.Dropdown(
                        label="季节",
                        choices=["春", "夏", "秋", "冬"],
                        value="秋",
                    )
                    notes_input = gr.Textbox(
                        label="补充说明（可选）",
                        placeholder="例如：今天不想穿外套 / 想显高",
                        lines=2,
                    )
                    rec_btn = gr.Button("🎨 生成搭配方案", variant="primary", size="lg")

                with gr.Column(scale=2):
                    outfit_display = gr.Markdown(label="搭配方案", value="*点击「生成搭配方案」开始*")

            gr.Markdown("---")
            gr.Markdown("### 👀 上身效果图")

            with gr.Row():
                with gr.Column(scale=1):
                    person_img_rec = gr.Image(
                        label="上传你的照片（正面站立效果最佳）",
                        type="filepath",
                        height=360,
                    )
                    outfit_selector = gr.Radio(
                        label="选择要试穿的套装",
                        choices=[],
                        interactive=True,
                    )
                    tryon_btn = gr.Button("👕 生成上身效果图", variant="primary", size="lg")
                    tryon_status = gr.Markdown()

                with gr.Column(scale=1):
                    tryon_result = gr.Image(label="上身效果图", height=480, show_download_button=True)

            rec_btn.click(
                recommend_outfits_fn,
                inputs=[occasion_input, style_input, season_input, notes_input],
                outputs=[outfit_display, outfit_selector, tryon_result],
            )
            tryon_btn.click(
                generate_tryon_fn,
                inputs=[person_img_rec, outfit_selector],
                outputs=[tryon_result, tryon_status],
            )

        # ── Tab 3: Quick Single Try-On ───────────────────────────
        with gr.Tab("🔬 单件快速试穿"):
            gr.Markdown("直接上传一张人物照片 + 一件衣服，快速测试试穿效果。")
            with gr.Row():
                with gr.Column():
                    person_img_single = gr.Image(label="人物照片", type="filepath", height=320)
                with gr.Column():
                    garment_img_single = gr.Image(label="衣服图片", type="filepath", height=320)

            with gr.Row():
                desc_single = gr.Textbox(label="衣服描述（有助于提升效果）", placeholder="例如：black oversized military jacket")
                cat_single = gr.Dropdown(
                    label="衣服类别",
                    choices=["upper_body", "lower_body", "dresses"],
                    value="upper_body",
                )
            single_btn = gr.Button("🚀 开始试穿", variant="primary")
            single_status = gr.Markdown()
            single_result = gr.Image(label="试穿结果", height=480, show_download_button=True)

            single_btn.click(
                single_tryon_fn,
                inputs=[person_img_single, garment_img_single, desc_single, cat_single],
                outputs=[single_result, single_status],
            )

        # ── Tab 4: Settings Info ─────────────────────────────────
        with gr.Tab("⚙️ 配置说明"):
            gr.Markdown("""
            ### 环境变量配置

            复制 `.env.example` 为 `.env`，填入你的 API Key：

            ```bash
            cp .env.example .env
            ```

            | 变量 | 说明 | 获取方式 |
            |---|---|---|
            | `OPENAI_API_KEY` | GPT-4o 接口，用于衣服分析和搭配推荐 | [platform.openai.com](https://platform.openai.com) |
            | `REPLICATE_API_TOKEN` | IDM-VTON 试穿模型 API | [replicate.com](https://replicate.com) |
            | `TRYON_BACKEND` | `replicate` 或 `huggingface` | 默认 replicate |

            ### 使用 HuggingFace 免费后端

            将 `TRYON_BACKEND=huggingface`，无需额外 Token，但速度较慢（排队等待）。

            ### HKU GPU Farm 部署

            详见 `scripts/run_on_gpu_farm.sh` 脚本说明。
            """)

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
        show_error=True,
    )
