#!/usr/bin/env python3
"""
Upload Moltbook posts to a LangSmith Tracing Project.

Usage:
    export LANGSMITH_API_KEY="your-api-key"
    python upload_to_tracing.py --input moltbook_posts.json --project moltbook-analysis

This creates traces formatted as conversations for use with the Insights Agent:
    - inputs.messages: [{"role": "user", "content": "Post by {author} in m/{submolt}: {title}"}]
    - outputs.messages: [{"role": "assistant", "content": "{post content}"}]
    - metadata: upvotes, comments, author info, timestamps
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from langsmith import Client


def upload_to_tracing(
    input_file: str,
    project_name: str = "moltbook-analysis",
    limit: int | None = None
):
    """
    Upload Moltbook posts to a LangSmith tracing project.
    
    Each post is formatted as a conversation trace for analysis
    with the LangSmith Insights Agent.
    
    Args:
        input_file: Path to JSON file with scraped posts
        project_name: Name for the LangSmith project
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
    
    # Get existing run IDs to avoid duplicates
    existing_ids = set()
    try:
        existing_runs = client.list_runs(project_name=project_name, limit=1000)
        for run in existing_runs:
            if run.extra and run.extra.get("metadata", {}).get("post_id"):
                existing_ids.add(run.extra["metadata"]["post_id"])
        if existing_ids:
            print(f"Found {len(existing_ids)} existing traces, will skip duplicates")
    except Exception:
        pass  # Project may not exist yet
    
    # Upload posts as traces
    success_count = 0
    skipped_count = 0
    
    for i, post in enumerate(posts):
        post_id = post["id"]
        
        if post_id in existing_ids:
            skipped_count += 1
            continue
        
        try:
            author = post["author"]["name"]
            submolt = post["submolt"]["name"]
            title = post["title"]
            content = post["content"]
            
            # Format as conversation
            inputs = {
                "messages": [
                    {"role": "user", "content": f"Post by {author} in m/{submolt}: {title}"}
                ]
            }
            
            outputs = {
                "messages": [
                    {"role": "assistant", "content": content}
                ]
            }
            
            metadata = {
                "post_id": post_id,
                "author": author,
                "author_id": post["author"]["id"],
                "submolt": submolt,
                "submolt_id": post["submolt"]["id"],
                "upvotes": post["upvotes"],
                "downvotes": post["downvotes"],
                "comment_count": post["comment_count"],
                "created_at": post["created_at"],
                "url": f"https://www.moltbook.com/post/{post_id}",
            }
            
            run_id = str(uuid.uuid4())
            
            client.create_run(
                name="moltbook_post",
                run_type="chain",
                inputs=inputs,
                outputs=outputs,
                project_name=project_name,
                id=run_id,
                start_time=datetime.fromisoformat(post["created_at"].replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(post["created_at"].replace("Z", "+00:00")),
                extra={"metadata": metadata}
            )
            
            success_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"  Uploaded {success_count} traces ({skipped_count} skipped)...")
                
        except Exception as e:
            print(f"  Error uploading post {post_id}: {e}")
    
    print(f"\nUploaded {success_count} new traces to project '{project_name}'")
    if skipped_count:
        print(f"   Skipped {skipped_count} duplicates")
    print(f"   View at: https://smith.langchain.com/projects")
    print(f"\nNext: Run the Insights Agent on this project to analyze AI agent behavior!")


def main():
    parser = argparse.ArgumentParser(description="Upload Moltbook posts to LangSmith tracing project")
    parser.add_argument("--input", "-i", type=str, default="moltbook_posts.json", help="Input JSON file")
    parser.add_argument("--project", "-p", type=str, default="moltbook-analysis", help="Project name")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Limit number of posts")
    
    args = parser.parse_args()
    
    upload_to_tracing(
        input_file=args.input,
        project_name=args.project,
        limit=args.limit
    )


if __name__ == "__main__":
    main()

