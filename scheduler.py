#!/usr/bin/env python3
"""
Scheduler for OpenRouter Stats Scraper

This script provides scheduling capabilities to run the stats scraper
automatically at specified intervals.

Usage:
    # Run once immediately
    python scheduler.py baidu/ernie-4.5-21b-a3b-thinking

    # Schedule daily at a specific time (24-hour format)
    python scheduler.py baidu/ernie-4.5-21b-a3b-thinking --schedule 08:00

    # Schedule with multiple models
    python scheduler.py baidu/ernie-4.5-21b-a3b-thinking openai/gpt-4 --schedule 08:00
"""

import argparse
import time
import schedule
import signal
import sys
from datetime import datetime
from pathlib import Path

from openrouter_stats_scraper import fetch_model_activity, save_to_json, save_to_csv, merge_historical_data, print_summary


def run_scraper(model_slugs: list, output_dir: Path, merge: bool = True, quiet: bool = False):
    """Run the scraper for all specified models."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Starting scheduled scrape...")

    for model_slug in model_slugs:
        print(f"\nProcessing: {model_slug}")

        data = fetch_model_activity(model_slug)
        if data is None:
            print(f"  Failed to fetch data for {model_slug}")
            continue

        print(f"  Retrieved {len(data)} data points")

        # Prepare paths
        safe_slug = model_slug.replace('/', '_')
        json_path = output_dir / f"{safe_slug}_activity.json"
        csv_path = output_dir / f"{safe_slug}_activity.csv"

        # Merge with historical data
        if merge and json_path.exists():
            data = merge_historical_data(data, json_path)
            print(f"  After merging: {len(data)} total data points")

        # Save files
        save_to_json(data, json_path, model_slug)
        save_to_csv(data, csv_path)

        # Print summary
        if not quiet:
            print_summary(data, model_slug)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scrape completed")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print("\n\nReceived interrupt signal. Shutting down...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Schedule OpenRouter stats scraping'
    )
    parser.add_argument(
        'model_slugs',
        nargs='+',
        help='One or more model slugs to track'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='./data',
        help='Output directory for data files (default: ./data)'
    )
    parser.add_argument(
        '--schedule',
        metavar='TIME',
        help='Time to run daily (24h format, e.g., 08:00). If not set, runs once.'
    )
    parser.add_argument(
        '--interval',
        type=int,
        metavar='HOURS',
        help='Run every N hours instead of daily at specific time'
    )
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='Do not merge with existing data'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress summary output'
    )

    args = parser.parse_args()

    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Define the job
    def job():
        run_scraper(
            args.model_slugs,
            output_dir,
            merge=not args.no_merge,
            quiet=args.quiet
        )

    # Run immediately first
    print("Running initial scrape...")
    job()

    # If scheduling is requested
    if args.schedule or args.interval:
        if args.schedule:
            schedule.every().day.at(args.schedule).do(job)
            print(f"\nScheduled to run daily at {args.schedule}")
        elif args.interval:
            schedule.every(args.interval).hours.do(job)
            print(f"\nScheduled to run every {args.interval} hours")

        print("Press Ctrl+C to stop.\n")

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == '__main__':
    main()
