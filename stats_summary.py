#!/usr/bin/env python3
"""
OpenRouter Statistics Summary

显示模型的关键统计数据：
1. 总调用量
2. 当前季度调用量
3. 当周调用量

Usage:
    python3 stats_summary.py
    python3 stats_summary.py --json
    python3 stats_summary.py --csv
"""

import argparse
import json
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_current_quarter_range():
    """获取当前季度的开始和结束日期"""
    today = datetime.now()
    quarter = (today.month - 1) // 3 + 1
    quarter_start_month = (quarter - 1) * 3 + 1
    quarter_start = datetime(today.year, quarter_start_month, 1)

    # 季度结束：下个季度开始的前一天
    if quarter == 4:
        quarter_end = datetime(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        quarter_end = datetime(today.year, quarter_start_month + 3, 1) - timedelta(days=1)

    return quarter_start, quarter_end, f"Q{quarter} {today.year}"


def get_current_week_range():
    """获取当周的开始和结束日期（上周五到这周五）"""
    today = datetime.now()
    
    # 计算本周五
    days_until_friday = (4 - today.weekday()) % 7  # 4 = Friday
    week_end = today + timedelta(days=days_until_friday)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # 上周五是本周五的前7天
    week_start = week_end - timedelta(days=7)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    return week_start, week_end


def load_model_data(json_path: Path) -> tuple:
    """加载模型数据，返回 (模型名, 数据列表)"""
    with open(json_path, 'r', encoding='utf-8') as f:
        content = json.load(f)

    model_name = content.get('model', json_path.stem)
    data = content.get('data', [])

    return model_name, data


def parse_date(date_str: str) -> datetime:
    """解析日期字符串"""
    # 格式: "2026-02-04 00:00:00"
    try:
        return datetime.strptime(date_str[:10], '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def calculate_stats(data: list) -> dict:
    """计算统计数据"""
    today = datetime.now()
    quarter_start, quarter_end, quarter_name = get_current_quarter_range()
    week_start, week_end = get_current_week_range()

    total_requests = 0
    quarter_requests = 0
    week_requests = 0

    total_tokens = 0
    quarter_tokens = 0
    week_tokens = 0

    first_date = None
    last_date = None

    for record in data:
        date = parse_date(record.get('date', ''))
        if date is None:
            continue

        count = record.get('count', 0)
        tokens = record.get('total_prompt_tokens', 0) + record.get('total_completion_tokens', 0)

        # 总量
        total_requests += count
        total_tokens += tokens

        # 日期范围
        if first_date is None or date < first_date:
            first_date = date
        if last_date is None or date > last_date:
            last_date = date

        # 当前季度
        if quarter_start <= date <= quarter_end:
            quarter_requests += count
            quarter_tokens += tokens

        # 当周
        if week_start <= date <= week_end:
            week_requests += count
            week_tokens += tokens

    return {
        'total_requests': total_requests,
        'total_tokens': total_tokens,
        'quarter_requests': quarter_requests,
        'quarter_tokens': quarter_tokens,
        'quarter_name': quarter_name,
        'week_requests': week_requests,
        'week_tokens': week_tokens,
        'week_start': week_start.strftime('%Y-%m-%d'),
        'week_end': week_end.strftime('%Y-%m-%d'),
        'first_date': first_date.strftime('%Y-%m-%d') if first_date else 'N/A',
        'last_date': last_date.strftime('%Y-%m-%d') if last_date else 'N/A',
        'num_days': len(data),
    }


def format_tokens(n: int) -> str:
    """格式化 token 数量，使用 K/M/B 单位"""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.2f}K"
    else:
        return str(n)


def print_table(all_stats: list):
    """打印统计表格（Token 数量）"""
    today = datetime.now()
    quarter_start, quarter_end, quarter_name = get_current_quarter_range()
    week_start, week_end = get_current_week_range()

    print(f"\n{'='*95}")
    print(f"OpenRouter 模型统计报告 (Token 使用量)")
    print(f"生成时间: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*95}")

    # 表头
    print(f"\n{'模型':<40} {'总 Token':>16} {quarter_name + ' Token':>18} {'本周 Token':>16}")
    print(f"{'-'*95}")

    # 数据行
    total_all = 0
    total_quarter = 0
    total_week = 0

    for item in all_stats:
        model = item['model']
        stats = item['stats']

        # 简化模型名称显示
        display_name = model.replace('baidu/', '')

        print(f"{display_name:<40} {format_tokens(stats['total_tokens']):>16} {format_tokens(stats['quarter_tokens']):>18} {format_tokens(stats['week_tokens']):>16}")

        total_all += stats['total_tokens']
        total_quarter += stats['quarter_tokens']
        total_week += stats['week_tokens']

    # 汇总行
    print(f"{'-'*95}")
    print(f"{'合计':<40} {format_tokens(total_all):>16} {format_tokens(total_quarter):>18} {format_tokens(total_week):>16}")

    # 附加信息
    print(f"\n{'='*95}")
    print(f"说明:")
    print(f"  - 当前季度: {quarter_name} ({quarter_start.strftime('%Y-%m-%d')} ~ {quarter_end.strftime('%Y-%m-%d')})")
    print(f"  - 本周范围: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
    if all_stats:
        print(f"  - 数据范围: {all_stats[0]['stats']['first_date']} ~ {all_stats[0]['stats']['last_date']} ({all_stats[0]['stats']['num_days']} 天)")
    print(f"{'='*95}\n")


def print_detailed(all_stats: list):
    """打印详细统计（包含 Token 数据）"""
    today = datetime.now()
    quarter_start, quarter_end, quarter_name = get_current_quarter_range()
    week_start, week_end = get_current_week_range()

    print(f"\n{'='*100}")
    print(f"OpenRouter 模型详细统计报告")
    print(f"生成时间: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*100}")

    for item in all_stats:
        model = item['model']
        stats = item['stats']

        print(f"\n📊 {model}")
        print(f"   {'─'*50}")
        print(f"   总调用量:        {stats['total_requests']:>15,} 次")
        print(f"   总 Token 数:     {stats['total_tokens']:>15,}")
        print(f"   {'─'*50}")
        print(f"   {quarter_name} 调用量:   {stats['quarter_requests']:>15,} 次")
        print(f"   {quarter_name} Token:    {stats['quarter_tokens']:>15,}")
        print(f"   {'─'*50}")
        print(f"   本周调用量:      {stats['week_requests']:>15,} 次")
        print(f"   本周 Token:      {stats['week_tokens']:>15,}")

    print(f"\n{'='*100}\n")


def export_json(all_stats: list, output_path: Path):
    """导出为 JSON"""
    today = datetime.now()
    quarter_start, quarter_end, quarter_name = get_current_quarter_range()
    week_start, week_end = get_current_week_range()

    output = {
        'generated_at': today.isoformat(),
        'quarter': {
            'name': quarter_name,
            'start': quarter_start.strftime('%Y-%m-%d'),
            'end': quarter_end.strftime('%Y-%m-%d'),
        },
        'week': {
            'start': week_start.strftime('%Y-%m-%d'),
            'end': week_end.strftime('%Y-%m-%d'),
        },
        'models': []
    }

    for item in all_stats:
        output['models'].append({
            'model': item['model'],
            'total_requests': item['stats']['total_requests'],
            'total_tokens': item['stats']['total_tokens'],
            'quarter_requests': item['stats']['quarter_requests'],
            'quarter_tokens': item['stats']['quarter_tokens'],
            'week_requests': item['stats']['week_requests'],
            'week_tokens': item['stats']['week_tokens'],
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"已导出到: {output_path}")


def export_csv(all_stats: list, output_path: Path):
    """导出为 CSV"""
    quarter_start, quarter_end, quarter_name = get_current_quarter_range()

    fieldnames = [
        'model',
        'total_requests', 'total_tokens',
        f'{quarter_name}_requests', f'{quarter_name}_tokens',
        'week_requests', 'week_tokens'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)

        for item in all_stats:
            stats = item['stats']
            writer.writerow([
                item['model'],
                stats['total_requests'], stats['total_tokens'],
                stats['quarter_requests'], stats['quarter_tokens'],
                stats['week_requests'], stats['week_tokens'],
            ])

    print(f"已导出到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='OpenRouter 模型统计汇总')
    parser.add_argument('--data-dir', '-d', default='./data', help='数据目录 (默认: ./data)')
    parser.add_argument('--json', metavar='FILE', help='导出 JSON 到指定文件')
    parser.add_argument('--csv', metavar='FILE', help='导出 CSV 到指定文件')
    parser.add_argument('--detailed', action='store_true', help='显示详细报告（包含 Token）')

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        return 1

    # 加载所有模型数据
    json_files = sorted(data_dir.glob('*_activity.json'))
    if not json_files:
        print(f"错误: 在 {data_dir} 中没有找到数据文件")
        return 1

    all_stats = []
    for json_path in json_files:
        model_name, data = load_model_data(json_path)
        if data:
            stats = calculate_stats(data)
            all_stats.append({
                'model': model_name,
                'stats': stats
            })

    if not all_stats:
        print("没有可用的统计数据")
        return 1

    # 按总调用量排序（降序）
    all_stats.sort(key=lambda x: x['stats']['total_requests'], reverse=True)

    # 输出
    if args.json:
        export_json(all_stats, Path(args.json))
    elif args.csv:
        export_csv(all_stats, Path(args.csv))
    elif args.detailed:
        print_detailed(all_stats)
    else:
        print_table(all_stats)

    return 0


if __name__ == '__main__':
    sys.exit(main())
