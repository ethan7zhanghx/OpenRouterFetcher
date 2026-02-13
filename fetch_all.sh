#!/bin/bash
# 一次性抓取所有百度模型的统计数据

MODELS=(
    "baidu/ernie-4.5-300b-a47b"
    "baidu/ernie-4.5-21b-a3b"
    "baidu/ernie-4.5-21b-a3b-thinking"
    "baidu/ernie-4.5-vl-424b-a47b"
    "baidu/ernie-4.5-vl-28b-a3b"
)

echo "开始抓取 ${#MODELS[@]} 个模型的数据..."
echo ""

for model in "${MODELS[@]}"; do
    echo ">>> 正在抓取: $model"
    python3 openrouter_stats_scraper.py "$model" -o ./data --merge --quiet
done

echo ""
echo "Done"
echo ""

# 显示对比
python3 analyze_stats.py data/baidu_*.json --compare
