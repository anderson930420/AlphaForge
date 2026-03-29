import requests
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

# === Load environment ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "http://127.0.0.1:27123"

DAILY_ROOT = "Daily"
PROJECT_ROOT = "01 Projects"


# === Helpers ===
def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def get_file_content(file_path):
    url = f"{BASE_URL}/vault/{file_path}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.text
    return ""


def write_file(file_path, content):
    url = f"{BASE_URL}/vault/{file_path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "text/markdown"
    }

    r = requests.put(url, data=content, headers=headers)

    if r.status_code not in (200, 204):
        print("❌ Path:", file_path)
        print("❌ Status:", r.status_code)
        print("❌ Response:", r.text)
    else:
        print(f"✅ Updated {file_path}")


def is_duplicate(existing, step_log):
    return step_log.strip() in existing


# === Core Logic ===
def append_to_daily(step_log):
    today = get_today()
    file_path = f"{DAILY_ROOT}/{today}.md"

    existing = get_file_content(file_path)
    section_title = "## 🤖 AI Work Log"

    # 🧠 去重（關鍵）
    if is_duplicate(existing, step_log):
        print("⚠️ Duplicate log skipped (Daily)")
        return

    if section_title in existing:
        parts = existing.split(section_title)
        before = parts[0]
        after = parts[1]

        updated = before + section_title + after + f"\n{step_log}\n"
    else:
        updated = f"""# {today}

## 🧠 Personal Notes

---

## 🤖 AI Work Log

{step_log}
"""

    write_file(file_path, updated)


def append_to_project(step_log, project):
    file_path = f"{PROJECT_ROOT}/{project}/worklog.md"

    existing = get_file_content(file_path)

    # 🧠 去重
    if is_duplicate(existing, step_log):
        print("⚠️ Duplicate log skipped (Project)")
        return

    updated = existing + f"\n{step_log}\n"
    write_file(file_path, updated)


def log(step_log, project=None):
    append_to_daily(step_log)

    if project:
        append_to_project(step_log, project)


# === CLI Entry ===
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 支援 txt 檔 or 直接字串
        if sys.argv[1].endswith(".txt"):
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                step_log = f.read()
        else:
            step_log = sys.argv[1]

        project = sys.argv[2] if len(sys.argv) > 2 else None
        log(step_log, project)

    else:
        # fallback 測試
        sample = """### [TEST] Logger working

- Action: test logger
- Files: obsidian_logger.py
- Reason: verify system
- Result: success
- Next: integrate with AI
"""
        log(sample, project="AlphaForge")