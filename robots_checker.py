
# robots_checker.py

import os
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = (
    "StudentWebCrawler/1.0 "
    "(Educational Research; contact: m1155508@mail.nuk.edu.tw, m1155511@mail.nuk.edu.tw, m1155528@mail.nuk.edu.tw)"
)



ROBOTS_DIR = "robots_data"

# 快取已載入的 robots.txt 規則
_robots_cache = {}


def get_robots_filepath(url):
    """依照 URL 的 scheme、hostname 與 port 找到本機規則檔。"""

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None

        host = parsed.hostname.lower()
        port = parsed.port

        # 預設 Port 不另外加入檔名
        default_port = (
            parsed.scheme == "http" and port in (None, 80)
        ) or (
            parsed.scheme == "https" and port in (None, 443)
        )

        if not default_port and port is not None:
            host = f"{host}_{port}"

        # 避免 IPv6 位址中的冒號影響檔名
        host = host.replace(":", "_")

        filename = f"{parsed.scheme}_{host}.txt"

        return os.path.join(ROBOTS_DIR, filename)

    except ValueError:
        # 例如 URL 中的 Port 格式錯誤
        return None


def _load_robots(url):
    """載入 URL 對應的本機 robots.txt。"""

    filepath = get_robots_filepath(url)

    if filepath is None:
        print(f"[ROBOTS BLOCKED] URL 格式無效：{url}")
        return None

    # 已載入過的規則直接使用快取
    if filepath in _robots_cache:
        return _robots_cache[filepath]

    if not os.path.isfile(filepath):
        print(f"[ROBOTS BLOCKED] 找不到規則檔：{filepath}")
        print("請先執行 robots_downloader.py。")
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()

        parser = RobotFileParser()
        parser.parse(lines)

        _robots_cache[filepath] = parser

        return parser

    except (OSError, UnicodeError) as exc:
        print(f"[ROBOTS ERROR] 無法讀取規則檔：{exc}")
        return None


def can_fetch(url):
    """
    判斷指定 URL 是否允許爬取。

    Returns:
        True: robots.txt 允許爬取
        False: 禁止爬取，或無法確認有效規則
    """

    parser = _load_robots(url)

    if parser is None:
        return False

    allowed = parser.can_fetch(USER_AGENT, url)

    if allowed:
        print(f"[ROBOTS ALLOWED] {url}")
    else:
        print(f"[ROBOTS BLOCKED] {url}")

    return allowed


def clear_cache():
    """清除規則快取，下次呼叫時重新讀取本機檔案。"""
    _robots_cache.clear()


if __name__ == "__main__":
    url = input("請輸入要檢查的完整 URL：").strip()

    if can_fetch(url):
        print("結果：允許爬取")
    else:
        print("結果：禁止爬取")
