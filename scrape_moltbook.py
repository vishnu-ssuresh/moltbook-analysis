#!/usr/bin/env python3
"""
Scrape top posts from Moltbook - the first social network for AI agents.

Usage:
    python scrape_moltbook.py --count 500 --output moltbook_posts.json

Features:
    - Batch fetching with configurable size
    - Automatic retries with exponential backoff
    - Checkpointing for crash recovery
    - Filters out posts with null title/content
"""

import argparse
import json
import os
import socket
import time
import urllib.request
import urllib.error
from typing import Optional

API_BASE = "https://www.moltbook.com/api/v1"
DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAY = 3


def fetch_posts(offset: int = 0, limit: int = 25, max_retries: int = 5, retry_delay: int = 3) -> Optional[dict]:
    """Fetch a batch of posts from the Moltbook API with retry logic."""
    url = f"{API_BASE}/posts?sort=top&limit={limit}&offset={offset}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MoltbookScraper/1.0")
            
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
                
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError) as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None
    return None


def is_valid_post(post: dict) -> bool:
    """Check if post has non-null title and content."""
    return post.get("title") is not None and post.get("content") is not None


def load_checkpoint(checkpoint_file: str) -> Optional[dict]:
    """Load checkpoint if it exists."""
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            print(f"Resuming from checkpoint: {len(checkpoint['posts'])} posts, offset {checkpoint['offset']}")
            return checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Checkpoint corrupted, starting fresh: {e}")
    return None


def save_checkpoint(checkpoint_file: str, posts: list, offset: int):
    """Save current progress to checkpoint file."""
    checkpoint = {
        "offset": offset,
        "posts": posts,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)


def save_output(output_file: str, posts: list):
    """Save posts to output file."""
    output = {
        "source": "moltbook.com",
        "description": "Top posts from Moltbook - the first social network for AI agents",
        "count": len(posts),
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "posts": posts
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def scrape_moltbook(
    count: int = 500,
    output_file: str = "moltbook_posts.json",
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    resume: bool = True
):
    """
    Scrape top posts from Moltbook.
    
    Args:
        count: Number of posts to fetch
        output_file: Output JSON file path
        batch_size: Posts per API request
        max_retries: Max retry attempts per request
        retry_delay: Base delay between retries (seconds)
        resume: Whether to resume from checkpoint
    """
    checkpoint_file = output_file.replace(".json", "_checkpoint.json")
    
    checkpoint = load_checkpoint(checkpoint_file) if resume else None
    
    if checkpoint:
        posts = checkpoint["posts"]
        offset = checkpoint["offset"]
    else:
        posts = []
        offset = 0
    
    print(f"\nScraping top {count} posts from Moltbook...")
    print(f"   Batch size: {batch_size} | Output: {output_file}\n")
    
    consecutive_failures = 0
    batch_num = 1
    
    while len(posts) < count:
        print(f"Batch {batch_num}: Fetching offset {offset}...")
        
        data = fetch_posts(offset=offset, limit=batch_size, max_retries=max_retries, retry_delay=retry_delay)
        
        if data is None:
            consecutive_failures += 1
            save_checkpoint(checkpoint_file, posts, offset + batch_size)
            save_output(output_file, posts)
            
            if consecutive_failures >= 3:
                print(f"\nWarning: Too many failures. Run again to resume from checkpoint.")
                return posts
            
            offset += batch_size
            batch_num += 1
            time.sleep(5)
            continue
        
        consecutive_failures = 0
        
        if not data.get("success") or not data.get("posts"):
            print(f"  No more posts available")
            break
        
        valid_posts = [p for p in data["posts"] if is_valid_post(p)]
        posts.extend(valid_posts)
        print(f"  Got {len(valid_posts)} posts (total: {len(posts)})")
        
        next_offset = data.get("next_offset", offset + batch_size)
        save_checkpoint(checkpoint_file, posts, next_offset)
        save_output(output_file, posts)
        
        if not data.get("has_more", False):
            break
        
        offset = next_offset
        batch_num += 1
        time.sleep(1)  # Rate limiting
    
    posts = posts[:count]
    save_output(output_file, posts)
    
    # Cleanup checkpoint
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
    
    print(f"\nDone! Saved {len(posts)} posts to {output_file}")
    return posts


def main():
    parser = argparse.ArgumentParser(description="Scrape top posts from Moltbook")
    parser.add_argument("--count", "-n", type=int, default=500, help="Number of posts to fetch (default: 500)")
    parser.add_argument("--output", "-o", type=str, default="moltbook_posts.json", help="Output file (default: moltbook_posts.json)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Batch size (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--no-resume", action="store_true", help="Don't resume from checkpoint")
    
    args = parser.parse_args()
    
    scrape_moltbook(
        count=args.count,
        output_file=args.output,
        batch_size=args.batch_size,
        resume=not args.no_resume
    )


if __name__ == "__main__":
    main()

