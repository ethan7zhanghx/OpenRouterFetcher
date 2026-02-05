#!/usr/bin/env python3
"""
Cron-friendly script to fetch all Baidu model stats.
Designed to be run once per day via cron job.

Usage:
    python3 cron_fetch.py

Cron example (every day at 8:00 AM):
    0 8 * * * cd /path/to/OpenRouter && python3 cron_fetch.py >> logs/fetch.log 2>&1
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add script directory to path
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

from openrouter_stats_scraper import fetch_model_activity, save_to_json, save_to_csv, merge_historical_data

# 要抓取的模型列表
MODELS = [
    "baidu/ernie-4.5-300b-a47b",
    "baidu/ernie-4.5-21b-a3b",
    "baidu/ernie-4.5-21b-a3b-thinking",
    "baidu/ernie-4.5-vl-424b-a47b",
    "baidu/ernie-4.5-vl-28b-a3b",
]

OUTPUT_DIR = script_dir / "data"


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{timestamp}] Starting daily fetch...")
    print(f"{'='*60}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for model_slug in MODELS:
        print(f"\n>>> {model_slug}")

        try:
            data = fetch_model_activity(model_slug)

            if data is None:
                print(f"    FAILED: No data returned")
                fail_count += 1
                continue

            # Prepare paths
            safe_slug = model_slug.replace('/', '_')
            json_path = OUTPUT_DIR / f"{safe_slug}_activity.json"
            csv_path = OUTPUT_DIR / f"{safe_slug}_activity.csv"

            # Merge with existing data
            if json_path.exists():
                data = merge_historical_data(data, json_path)

            # Save
            save_to_json(data, json_path, model_slug)
            save_to_csv(data, csv_path)

            # Summary
            total_requests = sum(r.get('count', 0) for r in data)
            print(f"    OK: {len(data)} days, {total_requests:,} total requests")
            success_count += 1

        except Exception as e:
            print(f"    ERROR: {e}")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"Completed: {success_count} success, {fail_count} failed")
    print(f"{'='*60}\n")

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
