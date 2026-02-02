# Moltbook Analysis

Scrape and analyze posts from [Moltbook](https://www.moltbook.com), the first social network for AI agents, using [LangSmith](https://smith.langchain.com).

## What is Moltbook?

Moltbook is a social network where AI agents post, comment, and interact autonomously. This repo provides tools to scrape posts and upload them to LangSmith for analysis with the Insights Agent.

## Setup

```bash
pip install -r requirements.txt
export LANGSMITH_API_KEY="your-langsmith-api-key"
```

## Usage

### 1. Scrape Posts

```bash
python scrape_moltbook.py --count 500 --output moltbook_posts.json
```

Features:
- Batch fetching with retries and exponential backoff
- Checkpointing for crash recovery
- Filters out posts with null title/content

### 2. Upload to LangSmith Dataset

```bash
python upload_to_dataset.py --input moltbook_posts.json --dataset moltbook_posts
```

Creates a dataset with:
- **inputs**: post title, author, submolt
- **outputs**: content, upvotes, comments
- **metadata**: author_id, timestamps, url

### 3. Upload to LangSmith Tracing Project

```bash
python upload_to_tracing.py --input moltbook_posts.json --project moltbook-analysis
```

Creates traces formatted as conversations for the Insights Agent:
- **inputs.messages**: `[{"role": "user", "content": "Post by {author} in m/{submolt}: {title}"}]`
- **outputs.messages**: `[{"role": "assistant", "content": "{content}"}]`

### 4. Run the Insights Agent

In LangSmith:
1. Go to your tracing project
2. Open the **Insights** tab
3. Run the Insights Agent with a custom prompt

Example prompt:
```
Analyze these posts from Moltbook - the first social network for AI agents.

Identify:
1. What topics dominate AI-to-AI discourse?
2. What unexpected behaviors or personas emerge?
3. Are agents cooperative or competitive?
4. What human social media patterns do they replicate vs. avoid?
5. What's genuinely novel about AI agent culture?
```
