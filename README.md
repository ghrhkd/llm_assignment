# AI 衣橱助手 — 穿搭推荐 + 虚拟试衣

基于 GPT-4o + IDM-VTON 的智能穿搭推荐与上身效果图生成系统。

## 功能

| 功能 | 技术 |
|---|---|
| 上传衣服照片，自动识别类别/颜色/风格 | GPT-4o Vision |
| 根据场合/风格/季节生成搭配方案 | GPT-4o + Prompt Engineering |
| 单件/多件套装上身效果图生成 | IDM-VTON (Replicate API) 或 OOTDiffusion (HuggingFace) |
| Web 界面 | Gradio |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY 和 REPLICATE_API_TOKEN
```

### 3. 启动

```bash
python main.py
# 浏览器访问 http://localhost:7860
```

## 批量导入衣橱

如果你已经有一个存放衣服照片的文件夹：

```bash
python scripts/batch_analyze_wardrobe.py --folder /path/to/your/clothes/photos
```

## 环境检查

```bash
python scripts/test_pipeline.py
```

## 项目结构

```
.
├── main.py                          # 启动入口
├── requirements.txt
├── .env.example                     # 环境变量模板
├── src/
│   ├── wardrobe/
│   │   ├── analyzer.py              # GPT-4o Vision 衣服分析
│   │   └── wardrobe_manager.py      # 衣橱数据库管理
│   ├── recommender/
│   │   └── outfit_recommender.py    # LLM 搭配推荐
│   ├── tryon/
│   │   ├── backends.py              # Replicate / HuggingFace 后端
│   │   └── pipeline.py             # 多件衣物顺序试穿流水线
│   └── ui/
│       └── app.py                   # Gradio Web UI
├── data/
│   ├── wardrobe_db/                 # 衣橱数据库和照片
│   └── outputs/                     # 生成的效果图
└── scripts/
    ├── batch_analyze_wardrobe.py    # 批量导入工具
    ├── test_pipeline.py             # 烟雾测试
    └── run_on_gpu_farm.sh           # HKU GPU Farm SLURM 脚本
```

## API 费用参考

| 服务 | 单价 | 100次调用 |
|---|---|---|
| GPT-4o（衣服分析） | ~$0.01/张 | ~$1 |
| GPT-4o（搭配推荐） | ~$0.03/次 | ~$3 |
| Replicate IDM-VTON | ~$0.05/张 | ~$5 |
| **合计原型阶段** | | **~$20 以内** |

## 后端切换

默认使用 Replicate（需要 API Token，约 $0.05/次）。
如需免费使用 HuggingFace 公共 Space（较慢，有排队）：

```bash
# 在 .env 中设置：
TRYON_BACKEND=huggingface
```

## HKU GPU Farm 部署

```bash
sbatch scripts/run_on_gpu_farm.sh
# Gradio 会生成一个公开分享链接（72小时有效）
```
