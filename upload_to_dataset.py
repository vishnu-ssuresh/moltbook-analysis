#!/usr/bin/env python3
"""
Upload Moltbook posts to a LangSmith Dataset.

Usage:
    export LANGSMITH_API_KEY="your-api-key"
    python upload_to_dataset.py --input moltbook_posts.json --dataset moltbook_posts

This creates a dataset where each post is stored as an example with:
    - inputs: post title, author, submolt
    - outputs: content, upvotes, comments
    - metadata: author_id, timestamps, url
"""

import argparse
import json
import os
from langsmith import Client


def upload_to_dataset(
    input_file: str,
    dataset_name: str = "moltbook_posts",
    limit: int | None = None
):
    """
    Upload Moltbook posts to a LangSmith dataset.
    
    Args:
        input_file: Path to JSON file with scraped posts
        dataset_name: Name for the LangSmith dataset
        limit: Optional limit on number of posts to upload
    """
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("Error: LANGSMITH_API_KEY environment variable not set")
        print("   Set it with: export LANGSMITH_API_KEY='your-api-key'")
        return
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    posts = data["posts"]
    if limit:
        posts = posts[:limit]
    
    print(f"Loaded {len(posts)} posts from {input_file}")
    
    client = Client()
    
    try:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Top posts from Moltbook - the first social network for AI agents"
        )
        print(f"Created new dataset: {dataset_name}")
    except Exception as e:
        if "already exists" in str(e).lower():
            dataset = client.read_dataset(dataset_name=dataset_name)
            print(f"Using existing dataset: {dataset_name}")
        else:
            raise e
    
    success_count = 0
    for i, post in enumerate(posts):
        try:
            inputs = {
                "post_id": post["id"],
                "title": post["title"],
                "author": post["author"]["name"],
                "submolt": post["submolt"]["name"],
                "created_at": post["created_at"],
            }
            
            outputs = {
                "content": post["content"],
                "upvotes": post["upvotes"],
                "downvotes": post["downvotes"],
                "comment_count": post["comment_count"],
            }
            
            metadata = {
                "author_id": post["author"]["id"],
                "submolt_id": post["submolt"]["id"],
                "submolt_display_name": post["submolt"]["display_name"],
                "url": f"https://www.moltbook.com/post/{post['id']}",
            }
            
            client.create_example(
                inputs=inputs,
                outputs=outputs,
                metadata=metadata,
                dataset_id=dataset.id
            )
            success_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"  Uploaded {i + 1}/{len(posts)} posts...")
                
        except Exception as e:
            print(f"  Error uploading post {post['id']}: {e}")
    
    print(f"\nUploaded {success_count}/{len(posts)} posts to dataset '{dataset_name}'")
    print(f"   View at: https://smith.langchain.com/datasets")


def main():
    parser = argparse.ArgumentParser(description="Upload Moltbook posts to LangSmith dataset")
    parser.add_argument("--input", "-i", type=str, default="moltbook_posts.json", help="Input JSON file")
    parser.add_argument("--dataset", "-d", type=str, default="moltbook_posts", help="Dataset name")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Limit number of posts")
    
    args = parser.parse_args()
    
    upload_to_dataset(
        input_file=args.input,
        dataset_name=args.dataset,
        limit=args.limit
    )


if __name__ == "__main__":
    main()

