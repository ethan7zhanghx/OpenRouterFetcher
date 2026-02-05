#!/usr/bin/env python3
"""
OpenRouter Model Statistics Scraper

This script scrapes daily usage statistics for any model on OpenRouter.
Data includes: request count, token usage, and other metrics per day.

Usage:
    python openrouter_stats_scraper.py <model_slug>
    python openrouter_stats_scraper.py baidu/ernie-4.5-21b-a3b-thinking

Features:
    - Fetches the last 30 days of activity data
    - Saves data to JSON and CSV formats
    - Supports scheduling for daily data collection
"""

import requests
import re
import json
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional


def fetch_model_activity(model_slug: str) -> Optional[list]:
    """
    Fetch activity data for a specific model from OpenRouter.

    Args:
        model_slug: The model identifier, e.g., 'baidu/ernie-4.5-21b-a3b-thinking'

    Returns:
        List of daily activity records, or None if failed
    """
    url = f"https://openrouter.ai/{model_slug}/activity"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Extract analytics data from the server-rendered response
        # The data is embedded in the page as part of Next.js RSC payload
        content = response.text

        # Find the analytics array in the response
        # The format in RSC payload uses escaped quotes: analytics\":[ or "analytics":[
        match = re.search(r'analytics["\']?\\*"?:\[(.*?)\]', content, re.DOTALL)
        if not match:
            print(f"Warning: Could not find analytics data in response for {model_slug}")
            return None

        array_content = match.group(1)

        # Parse individual records
        records = []
        # Match JSON objects within the array - handle both escaped and unescaped quotes
        # First, try to normalize the escaped quotes
        normalized = array_content.replace('\\"', '"').replace("\\'", "'")

        # Match JSON objects
        pattern = r'\{[^{}]+\}'
        for item_match in re.finditer(pattern, normalized):
            try:
                record = json.loads(item_match.group(0))
                records.append(record)
            except json.JSONDecodeError:
                continue

        return records

    except requests.RequestException as e:
        print(f"Error fetching data for {model_slug}: {e}")
        return None


def save_to_json(data: list, output_path: Path, model_slug: str):
    """Save activity data to a JSON file."""
    output = {
        "model": model_slug,
        "fetched_at": datetime.now().isoformat(),
        "data": data
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved JSON to: {output_path}")


def save_to_csv(data: list, output_path: Path):
    """Save activity data to a CSV file."""
    if not data:
        print("No data to save to CSV")
        return

    # Get all unique keys from the data
    fieldnames = set()
    for record in data:
        fieldnames.update(record.keys())
    fieldnames = sorted(fieldnames)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Saved CSV to: {output_path}")


def merge_historical_data(new_data: list, existing_file: Path) -> list:
    """
    Merge new data with existing historical data.
    Keeps the most recent record for each date.
    """
    if not existing_file.exists():
        return new_data

    try:
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)

        existing_data = existing.get('data', [])

        # Create a dict keyed by date for easy merging
        data_by_date = {}
        for record in existing_data:
            date = record.get('date', '')
            data_by_date[date] = record

        # Update with new data (overwrites existing dates)
        for record in new_data:
            date = record.get('date', '')
            data_by_date[date] = record

        # Sort by date descending
        merged = sorted(data_by_date.values(),
                       key=lambda x: x.get('date', ''),
                       reverse=True)

        return merged

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not merge with existing data: {e}")
        return new_data


def print_summary(data: list, model_slug: str):
    """Print a summary of the fetched data."""
    if not data:
        print("No data available")
        return

    print(f"\n{'='*60}")
    print(f"Model: {model_slug}")
    print(f"{'='*60}")
    print(f"Data points: {len(data)} days")

    if data:
        # Sort by date
        sorted_data = sorted(data, key=lambda x: x.get('date', ''), reverse=True)

        # Show recent days
        print(f"\nRecent Activity (last 7 days):")
        print(f"{'Date':<20} {'Requests':>10} {'Prompt Tokens':>15} {'Completion Tokens':>18}")
        print("-" * 65)

        for record in sorted_data[:7]:
            date = record.get('date', '')[:10]
            count = record.get('count', 0)
            prompt_tokens = record.get('total_prompt_tokens', 0)
            completion_tokens = record.get('total_completion_tokens', 0)
            print(f"{date:<20} {count:>10,} {prompt_tokens:>15,} {completion_tokens:>18,}")

        # Calculate totals
        total_requests = sum(r.get('count', 0) for r in data)
        total_prompt = sum(r.get('total_prompt_tokens', 0) for r in data)
        total_completion = sum(r.get('total_completion_tokens', 0) for r in data)

        print("-" * 65)
        print(f"\nTotals (all {len(data)} days):")
        print(f"  Total Requests: {total_requests:,}")
        print(f"  Total Prompt Tokens: {total_prompt:,}")
        print(f"  Total Completion Tokens: {total_completion:,}")
        print(f"  Total Tokens: {total_prompt + total_completion:,}")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape OpenRouter model usage statistics'
    )
    parser.add_argument(
        'model_slug',
        help='Model slug, e.g., baidu/ernie-4.5-21b-a3b-thinking'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='./data',
        help='Output directory for data files (default: ./data)'
    )
    parser.add_argument(
        '--merge',
        action='store_true',
        help='Merge with existing historical data'
    )
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Only save JSON format'
    )
    parser.add_argument(
        '--csv-only',
        action='store_true',
        help='Only save CSV format'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress summary output'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize model slug for filename
    safe_slug = args.model_slug.replace('/', '_')

    # Fetch data
    print(f"Fetching activity data for: {args.model_slug}")
    data = fetch_model_activity(args.model_slug)

    if data is None:
        print("Failed to fetch data")
        return 1

    print(f"Retrieved {len(data)} data points")

    # Merge with historical data if requested
    json_path = output_dir / f"{safe_slug}_activity.json"
    if args.merge:
        data = merge_historical_data(data, json_path)
        print(f"After merging: {len(data)} total data points")

    # Save files
    if not args.csv_only:
        save_to_json(data, json_path, args.model_slug)

    if not args.json_only:
        csv_path = output_dir / f"{safe_slug}_activity.csv"
        save_to_csv(data, csv_path)

    # Print summary
    if not args.quiet:
        print_summary(data, args.model_slug)

    return 0


if __name__ == '__main__':
    exit(main())
