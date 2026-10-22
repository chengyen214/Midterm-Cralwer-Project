
import os
import requests
from urllib.parse import urlparse

USER_AGENT = (
    "StudentWebCrawler/1.0 "
    "(Educational Research; contact: your-email@example.com)"
)

SAVE_DIR = "robots_data"
TIMEOUT = 10


def download_robots(site_url):
    """下載網站 robots.txt 並儲存至本機。"""

    parsed = urlparse(site_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print("[ERROR] 請提供有效的 HTTP/HTTPS 網址")
        return None

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    os.makedirs(SAVE_DIR, exist_ok=True)

    # 使用 scheme 與 host 建立檔名，避免不同網站互相覆蓋
    filename = f"{parsed.scheme}_{parsed.netloc.replace(':', '_')}.txt"
    filepath = os.path.join(SAVE_DIR, filename)

    try:
        response = requests.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=False
        )

        # 不把錯誤頁面存成有效的 robots.txt
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code}: {robots_url}")
            return None

        with open(filepath, "w", encoding="utf-8") as file:
            file.write(response.text)

        print(f"[SUCCESS] robots.txt 已儲存：{filepath}")
        print(f"[SOURCE] {robots_url}")

        return filepath

    except requests.RequestException as exc:
        print(f"[ERROR] 下載失敗：{exc}")
        return None


if __name__ == "__main__":
    site = input("請輸入網站網址，例如 https://example.com/：").strip()
    download_robots(site)
