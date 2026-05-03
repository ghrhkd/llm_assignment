#!/usr/bin/env python3
"""
批量运行 ComfyUI Clothing Matching 工作流
25轮 × 每轮3次 = 共75次
- 第i轮：4号节点选 upper_i，22号节点选 bottom_i
- 第i轮第j次：2号节点选 original_1，50号节点选 face_i（循环使用3张face图）
- 输出：clothing_match_run{i}_face{j}.png
"""

import json
import uuid
import random
import urllib.request
import urllib.parse
import websocket
import os
import sys

SERVER = "127.0.0.1:8188"
WORKFLOW_PATH = "Clothing Matching Workflow.json"
OUTPUT_DIR = "../comfyui/output"
COMFYUI_INPUT_DIR = "../comfyui/ComfyUI/input"

DATASET_DIR = "../comfyui/dataset_raw"
ROUNDS = 25
RUNS_PER_ROUND = 3
FACE_COUNT = 3  # face 目录现有图片数（face_1~3）


def symlink_images_to_input():
    """将所需图片软链接到 ComfyUI input 目录"""
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)

    link_map = {}

    # original: 只需 original_1.png
    src = os.path.join(DATASET_DIR, "original", "original_1.png")
    if os.path.exists(src):
        link_map["original_1.png"] = src

    # face: face_1~3.png（循环使用）
    for i in range(1, FACE_COUNT + 1):
        src = os.path.join(DATASET_DIR, "face", f"face_{i}.png")
        if os.path.exists(src):
            link_map[f"face_{i}.png"] = src

    # upper: thisisneverthat_jk001_1~25.jpg
    for i in range(1, ROUNDS + 1):
        src = os.path.join(DATASET_DIR, "thisisneverthat_upper", f"thisisneverthat_jk001_{i}.jpg")
        if os.path.exists(src):
            link_map[f"thisisneverthat_jk001_{i}.jpg"] = src
        else:
            print(f"⚠️ 缺少: {src}")

    # bottom: thisisneverthat_bottom_1~25.jpg
    for i in range(1, ROUNDS + 1):
        src = os.path.join(DATASET_DIR, "thisisneverthat_bottom", f"thisisneverthat_bottom_{i}.jpg")
        if os.path.exists(src):
            link_map[f"thisisneverthat_bottom_{i}.jpg"] = src
        else:
            print(f"⚠️ 缺少: {src}")

    created = 0
    for name, src in link_map.items():
        dst = os.path.join(COMFYUI_INPUT_DIR, name)
        if os.path.exists(dst) or os.path.islink(dst):
            continue
        os.symlink(src, dst)
        created += 1

    print(f"已创建 {created} 个软链接到 ComfyUI input 目录")


def queue_prompt(prompt, client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=data)
    response = urllib.request.urlopen(req)
    result = json.loads(response.read())
    return result.get("prompt_id", str(uuid.uuid4()))


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER}/view?{url_values}") as response:
        return response.read()


def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{SERVER}/history/{prompt_id}") as response:
        return json.loads(response.read())


def wait_for_execution(ws, prompt_id):
    """通过 websocket 等待工作流执行完成"""
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            msg_type = message.get("type", "")
            data = message.get("data", {})
            if msg_type == "execution_error":
                print(f"  ❌ 执行出错: {data}")
                return False
            if msg_type == "executing":
                if data.get("node") is None and data.get("prompt_id") == prompt_id:
                    return True
        else:
            continue


def run_once(workflow, round_i, run_j):
    """执行一次工作流，保存最终输出为 clothing_match_run{i}_face{j}.png"""
    # 设置节点输入
    workflow["4"]["inputs"]["image"] = f"thisisneverthat_jk001_{round_i}.jpg"
    workflow["22"]["inputs"]["image"] = f"thisisneverthat_bottom_{round_i}.jpg"
    workflow["2"]["inputs"]["image"] = "original_1.png"
    workflow["50"]["inputs"]["image"] = f"face_{run_j}.png"

    # 随机 seed
    for node_id, node in workflow.items():
        if "seed" in node.get("inputs", {}):
            workflow[node_id]["inputs"]["seed"] = random.randint(0, 2**63)

    # 输出前缀（ComfyUI 会自动追加 _00001_ 等后缀，我们后面手动重命名）
    workflow["31"]["inputs"]["filename_prefix"] = f"clothing_match_run{round_i}_face{run_j}"

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(workflow, client_id)

    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER}/ws?clientId={client_id}")
    try:
        success = wait_for_execution(ws, prompt_id)
    finally:
        ws.close()

    if not success:
        return None

    # 获取输出图片
    history = get_history(prompt_id)
    if prompt_id not in history:
        print(f"  ⚠️ 未找到执行历史")
        return None

    outputs = history[prompt_id].get("outputs", {})

    # 只取 SaveImage 节点(31)的最终输出
    if "31" not in outputs or "images" not in outputs["31"]:
        print(f"  ⚠️ 节点31无输出")
        return None

    image_info = outputs["31"]["images"][0]
    image_data = get_image(
        image_info["filename"],
        image_info.get("subfolder", ""),
        image_info.get("type", "output"),
    )

    out_filename = f"clothing_match_run{round_i}_face{run_j}.png"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    with open(out_path, "wb") as f:
        f.write(image_data)

    return out_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: 软链接图片到 ComfyUI input
    symlink_images_to_input()

    # Step 2: 加载工作流
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    print(f"\n📋 已加载工作流: {WORKFLOW_PATH}")
    print(f"🔄 25轮 × 每轮3次 = 共75次执行\n")

    success_count = 0
    fail_count = 0

    for i in range(1, ROUNDS + 1):
        print(f"━━━ 第 {i}/{ROUNDS} 轮 ━━━")
        for j in range(1, RUNS_PER_ROUND + 1):
            face_idx = ((i - 1) % FACE_COUNT) + 1
            print(f"  [{i}-{j}] upper={i}, bottom={i}, original=1, face={face_idx} ... ", end="", flush=True)
            result = run_once(workflow, i, j)
            if result:
                print(f"✅ → {os.path.basename(result)}")
                success_count += 1
            else:
                print(f"❌ 失败")
                fail_count += 1

    print(f"\n🎉 全部完成！成功 {success_count} 次，失败 {fail_count} 次")
    print(f"📁 输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
