import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "http://127.0.0.1:27123"

DAILY_ROOT = "Daily"
PROJECT_ROOT = "01 Projects"


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def read_file(path):
    url = f"{BASE_URL}/vault/{path}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.text
    return ""


def main():
    today = get_today()

    daily_path = f"{DAILY_ROOT}/{today}.md"
    project_path = f"{PROJECT_ROOT}/AlphaForge/worklog.md"

    daily = read_file(daily_path)
    project = read_file(project_path)

    print("===== DAILY =====")
    print(daily)

    print("\n===== PROJECT =====")
    print(project)


if __name__ == "__main__":
    main()