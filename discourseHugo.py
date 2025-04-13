#!/usr/bin/env python3
# discourse_to_hugo.py - Convert Discourse threads with specific tags to Hugo posts

import os
import requests
import frontmatter
from datetime import datetime
import html2text
import subprocess
import shutil

# ===== CONFIGURATION =====
DISCOURSE_URL = "https://forum.santricyber.dev"
DISCOURSE_API_KEY = os.getenv("DISCOURSE_API_KEY")
DISCOURSE_USERNAME = "syafmovic"

ALLOWED_TAGS = {"blog", "news", "information", "feature"}

GITHUB_REPO = "https://github.com/santricyber/blog.git"
GITHUB_BRANCH = "main"
CONTENT_DIR = "content/posts"
# ==========================

HEADERS = {
    "Api-Key": DISCOURSE_API_KEY,
    "Api-Username": DISCOURSE_USERNAME
}

def fetch_latest_threads():
    """Ambil thread terbaru dari Discourse dan filter berdasarkan tag"""
    try:
        response = requests.get(f"{DISCOURSE_URL}/latest.json", headers=HEADERS, timeout=10)
        response.raise_for_status()
        threads = response.json()["topic_list"]["topics"]

        return [t for t in threads if set(t.get("tags", [])) & ALLOWED_TAGS]
    except Exception as e:
        print(f"⚠️ Error fetching threads: {e}")
        return []

def fetch_post_content(thread_id):
    """Ambil konten post pertama dari thread"""
    try:
        post_url = f"{DISCOURSE_URL}/t/{thread_id}.json"
        post_data = requests.get(post_url, headers=HEADERS).json()
        return post_data["post_stream"]["posts"][0]["cooked"]
    except Exception as e:
        print(f"⚠️ Error fetching post content for thread {thread_id}: {e}")
        return ""

def convert_to_markdown(thread, content_html):
    """Konversi thread dan HTML-nya ke markdown Hugo"""
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_links = False
    content_md = h.handle(content_html)

    created = datetime.strptime(thread['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
    filename = f"{created.strftime('%Y-%m-%d')}-{thread['slug']}.md"

    markdown = f"""---
title: "{thread['title']}"
date: {created.isoformat()}
author: "{thread['poster_user_slug']}"
discourse:
  url: "{DISCOURSE_URL}/t/{thread['slug']}/{thread['id']}"
  id: {thread['id']}
  views: {thread['views']}
tags: {thread.get('tags', [])}
categories: ["forum"]
---

{{%% discourse_meta %%}}
**💬 Artikel pilihan dari Forum**: [Baca di Discourse]({DISCOURSE_URL}/t/{thread['slug']}/{thread['id']})  
**👀 {thread['views']} Views**
{{%% /discourse_meta %%}}

{content_md}

[🔗 Lanjut baca di forum]({DISCOURSE_URL}/t/{thread['slug']}/{thread['id']})
"""
    return filename, markdown

def save_and_push(threads):
    """Simpan file markdown ke Hugo repo dan push ke GitHub"""
    repo_dir = "hugo-content-temp"
    
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    subprocess.run(["git", "clone", "--depth=1", "-b", GITHUB_BRANCH, GITHUB_REPO, repo_dir], check=True)

    saved = 0
    for thread in threads:
        content_html = fetch_post_content(thread['id'])
        if not content_html:
            continue

        filename, markdown = convert_to_markdown(thread, content_html)
        filepath = os.path.join(repo_dir, CONTENT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"✅ Saved: {filename}")
        saved += 1

    if saved == 0:
        print("ℹ️ Tidak ada thread baru yang diproses.")
        return

    subprocess.run(["git", "-C", repo_dir, "config", "user.name", "Discourse Bot"], check=True)
    subprocess.run(["git", "-C", repo_dir, "config", "user.email", "bot@santricyber.dev"], check=True)
    subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", f"Auto-import {saved} threads from Discourse"], check=True)
    subprocess.run(["git", "-C", repo_dir, "push"], check=True)

    print("🚀 Sukses push ke GitHub!")

if __name__ == "__main__":
    print("🔍 Mencari thread dengan tag:", ", ".join(ALLOWED_TAGS))
    threads = fetch_latest_threads()

    if not threads:
        print("⚠️ Tidak ada thread yang cocok.")
    else:
        print(f"📦 Memproses {len(threads)} thread...")
        save_and_push(threads)