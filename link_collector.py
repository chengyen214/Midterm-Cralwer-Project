
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urldefrag

import requests
from bs4 import BeautifulSoup

from robots_checker import can_fetch


# ==================================================
# 1. 設定
# ==================================================

TARGET_SITES = [
    "https://thenewstack.io/",
    "https://techcrunch.com/category/artificial-intelligence/",
    "https://spectrum.ieee.org/topic/artificial-intelligence/",
    "https://arstechnica.com/ai/",
    "https://www.infoq.com/ai-ml-data-eng/news/?_gl=1*p9ow3x*_up*MQ..*_ga*ODgwNzgyMjI2LjE3OTI4MDk1OTc.*_ga_VMVPD4D2JY*czE3OTI4MDk1OTYkbzEkZzEkdDE3OTI4MDk2MjckajI5JGwwJGgw",
    "https://www.engadget.com/category/ai/",
    "https://venturebeat.com/category/technology",
]

# 網域規則或「網域/路徑前綴」規則
TARGET_LINKS = [
    "thenewstack.io",
    "techcrunch.com",
    "spectrum.ieee.org",
    "arstechnica.com",
    "infoq.com/news/",
    "engadget.com",
    "venturebeat.com/technology/",
]

FILTERED_LINKS = []
OUTPUT_FILE = Path("filtered_links.json")

USER_AGENT = (
    "StudentWebCrawler/1.0 "
    "(Educational Research; contact: m1155508@mail.nuk.edu.tw, m1155511@mail.nuk.edu.tw, m1155528@mail.nuk.edu.tw)"
)



TIMEOUT = 10
MAX_ATTEMPTS = 3000
MAX_REDIRECTS = 5

HOST_INTERVALS = {
    "thenewstack.io": 2,
    "techcrunch.com": 2,
    "spectrum.ieee.org": 2,
    "arstechnica.com": 2,
    "infoq.com": 3,
    "engadget.com": 2,
    "venturebeat.com": 2,
}

LAST_REQUEST_TIME = {}


# ==================================================
# 2. URL 處理
# ==================================================

def normalize_url(url):
    """只移除 fragment，保留 query parameters。"""
    try:
        parts = urlsplit(url)

        if parts.scheme.lower() not in ("http", "https"):
            return None

        if not parts.hostname:
            return None

        if parts.username or parts.password:
            return None

        if parts.port not in (None, 80, 443):
            return None

        url, _ = urldefrag(url)
        return url

    except (TypeError, ValueError):
        return None


def matches_target_link(url):
    """
    TARGET_LINKS 可設定：
    1. 網域，例如 techcrunch.com
    2. 網域及路徑前綴，例如 infoq.com/news/
    """
    try:
        parts = urlsplit(url)

        if parts.scheme.lower() not in ("http", "https"):
            return False

        hostname = (parts.hostname or "").lower()
        path = parts.path or "/"

        if parts.port not in (None, 80, 443):
            return False

        for rule in TARGET_LINKS:
            rule = rule.strip().lower()

            if "/" in rule:
                domain, path_prefix = rule.split("/", 1)
                path_prefix = "/" + path_prefix

                if not path_prefix.endswith("/"):
                    path_prefix += "/"

                domain_matches = (
                    hostname == domain
                    or hostname.endswith("." + domain)
                )

                # 同時接受該路徑本身及其子路徑
                base_path = path_prefix.rstrip("/")

                path_matches = (
                    path == base_path
                    or path.startswith(path_prefix)
                )

                if domain_matches and path_matches:
                    return True

            else:
                if (
                    hostname == rule
                    or hostname.endswith("." + rule)
                ):
                    return True

        return False

    except (TypeError, ValueError):
        return False


# ==================================================
# 3. robots.txt 檢查
# ==================================================

def is_allowed_by_robots(url):
    """
    使用 robots_checker.py 的 can_fetch(url)。
    若規則檔不存在或檢查發生錯誤，預設拒絕。
    """
    try:
        return can_fetch(url)
    except Exception as exc:
        print(f"[ROBOTS ERROR] {url}: {exc}")
        return False



def preflight_seed_sites():
    """
    先檢查所有 TARGET_SITES 的 URL 格式與 robots.txt。
    不使用 TARGET_LINKS 篩選 Seed。
    只要一個 Seed 不通過，就不開始下載任何 HTML。
    """
    print("=" * 65)
    print("第一階段：預先檢查所有 TARGET_SITES 的 robots.txt")
    print("=" * 65)

    results = []

    for seed_url in TARGET_SITES:
        normalized = normalize_url(seed_url)

        if normalized is None:
            results.append((seed_url, False, "URL 格式無效"))
            print(f"[FAIL] URL 格式無效：{seed_url}")
            continue

        # 注意：這裡不檢查 TARGET_LINKS
        if not is_allowed_by_robots(normalized):
            results.append(
                (seed_url, False, "robots 不允許或無法確認")
            )
            print(f"[FAIL] robots 不允許或無法確認：{seed_url}")
            continue

        results.append((seed_url, True, "robots 允許"))
        print(f"[PASS] {seed_url}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    print("-" * 65)
    print(f"Seed 總數：{len(TARGET_SITES)}")
    print(f"通過：{passed}")
    print(f"未通過：{failed}")
    print("-" * 65)

    if failed:
        print("[STOP] 並非所有 Seed 都通過 robots 檢查。")
        print("不會下載任何 HTML，請先確認 robots_data 規則檔。")
        return False

    print("[PASS] 所有 Seed 均通過 robots 檢查，可以開始下載 HTML。")
    return True


# ==================================================
# 4. 請求間隔
# ==================================================

def get_host_interval(url):
    hostname = (urlsplit(url).hostname or "").lower()

    for domain, interval in HOST_INTERVALS.items():
        if hostname == domain or hostname.endswith("." + domain):
            return interval

    return 2


def wait_for_host(url):
    """同一個 hostname 的請求至少間隔指定秒數。"""
    hostname = (urlsplit(url).hostname or "").lower()
    interval = get_host_interval(url)
    previous = LAST_REQUEST_TIME.get(hostname)

    if previous is not None:
        elapsed = time.monotonic() - previous
        remaining = interval - elapsed

        if remaining > 0:
            time.sleep(remaining)


# ==================================================
# 5. 下載 HTML（逐次檢查重新導向）
# ==================================================

def download_html(session, url, attempt_counter):
    """
    下載 Seed HTML。
    每次請求前都檢查範圍與 robots。
    手動處理重新導向，避免自動跟隨到未允許的網址。
    """
    current_url = normalize_url(url)

    if not current_url:
        print(f"[SKIP] 無效 URL：{url}")
        return None, None

    for redirect_count in range(MAX_REDIRECTS + 1):
        if attempt_counter[0] >= MAX_ATTEMPTS:
            print("[STOP] 已達最大請求次數。")
            return None, None

        if not matches_target_link(current_url):
            print(f"[SKIP] 網址超出目標範圍：{current_url}")
            return None, None

        if not is_allowed_by_robots(current_url):
            print(f"[SKIP] robots 不允許：{current_url}")
            return None, None

        wait_for_host(current_url)

        hostname = (urlsplit(current_url).hostname or "").lower()
        LAST_REQUEST_TIME[hostname] = time.monotonic()
        attempt_counter[0] += 1

        try:
            response = session.get(
                current_url,
                timeout=TIMEOUT,
                allow_redirects=False,
            )

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")

                if not location:
                    print(f"[ERROR] 重新導向沒有 Location：{current_url}")
                    return None, None

                next_url = normalize_url(urljoin(current_url, location))

                if not next_url:
                    print(f"[SKIP] 無效的重新導向網址：{location}")
                    return None, None

                if not matches_target_link(next_url):
                    print(f"[SKIP] 重新導向超出目標範圍：{next_url}")
                    return None, None

                if not is_allowed_by_robots(next_url):
                    print(f"[SKIP] 重新導向目的地 robots 不允許：{next_url}")
                    return None, None

                response.close()
                current_url = next_url
                continue

            if response.status_code in (403, 429):
                print(
                    f"[STOP] HTTP {response.status_code}：{current_url}"
                )
                response.close()
                return None, None

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "text/html" not in content_type:
                print(f"[SKIP] 非 HTML 回應：{current_url}")
                response.close()
                return None, None

            html = response.text
            status = response.status_code
            response.close()

            print(f"[HTML DOWNLOADED] HTTP {status}: {current_url}")
            return html, current_url

        except requests.RequestException as exc:
            print(f"[DOWNLOAD ERROR] {current_url}: {exc}")
            return None, None

    print(f"[STOP] 重新導向次數超過限制：{url}")
    return None, None


# ==================================================
# 6. 擷取並篩選連結
# ==================================================

def collect_html_links(html, page_url, existing_set):
    soup = BeautifulSoup(html, "html.parser")

    found_count = 0
    added_count = 0
    rejected_count = 0

    for anchor in soup.find_all("a", href=True):
        absolute_url = urljoin(page_url, anchor["href"])
        normalized = normalize_url(absolute_url)

        if not normalized:
            rejected_count += 1
            continue

        if not matches_target_link(normalized):
            rejected_count += 1
            continue

        # 這裡只檢查連結是否允許；不會下載該連結的 HTML
        if not is_allowed_by_robots(normalized):
            rejected_count += 1
            continue

        found_count += 1

        if normalized not in existing_set:
            existing_set.add(normalized)
            FILTERED_LINKS.append(normalized)
            added_count += 1

    return found_count, added_count, rejected_count


# ==================================================
# 7. 載入既有連結
# ==================================================

def load_existing_links():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("filtered_links.json 最外層必須是陣列。")

    result = []
    seen = set()

    for url in data:
        if not isinstance(url, str):
            continue

        normalized = normalize_url(url)

        if (
            normalized
            and matches_target_link(normalized)
            and normalized not in seen
            and is_allowed_by_robots(normalized)
        ):
            result.append(normalized)
            seen.add(normalized)

    return result


# ==================================================
# 8. 主程式
# ==================================================

def collect_links():
    FILTERED_LINKS.clear()
    LAST_REQUEST_TIME.clear()

    # 第一階段：全部 Seed 預檢
    # 任何一個不通過，都不會開始下載 HTML
    if not preflight_seed_sites():
        return

    # 第二階段：預檢通過後，才載入舊結果及下載 HTML
    try:
        old_links = load_existing_links()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ERROR] 無法讀取舊有結果：{exc}")
        return

    FILTERED_LINKS.extend(old_links)
    existing_set = set(FILTERED_LINKS)

    attempt_counter = [0]
    successful_sites = 0
    failed_sites = 0
    total_found = 0
    total_added = 0
    total_rejected = 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("\n" + "=" * 65)
    print("第二階段：開始下載 Seed HTML 並收集連結")
    print(f"Seed 網站數：{len(TARGET_SITES)}")
    print(f"載入舊有有效網址：{len(old_links)}")
    print("=" * 65)

    try:
        for seed_url in TARGET_SITES:
            if attempt_counter[0] >= MAX_ATTEMPTS:
                print("[STOP] 已達最大請求次數。")
                break

            print(f"\n[SEED] {seed_url}")

            html, final_url = download_html(
                session,
                seed_url,
                attempt_counter,
            )

            if html is None:
                failed_sites += 1
                continue

            found, added, rejected = collect_html_links(
                html,
                final_url,
                existing_set,
            )

            successful_sites += 1
            total_found += found
            total_added += added
            total_rejected += rejected

            print(f"[INFO] 符合條件的連結：{found}")
            print(f"[INFO] 新增不重複連結：{added}")
            print(f"[INFO] 排除連結：{rejected}")

    finally:
        session.close()

    # 儲存篩選結果
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            FILTERED_LINKS,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with OUTPUT_FILE.open("r", encoding="utf-8") as file:
        saved_links = json.load(file)

    print("\n" + "=" * 65)
    print("最終統計")
    print("=" * 65)
    print(f"Seed 網站總數：{len(TARGET_SITES)}")
    print(f"成功下載 HTML：{successful_sites}")
    print(f"下載失敗：{failed_sites}")
    print(f"符合條件的連結：{total_found}")
    print(f"新增不重複連結：{total_added}")
    print(f"排除連結：{total_rejected}")
    print(f"FILTERED_LINKS 總數：{len(set(FILTERED_LINKS))}")
    print(f"JSON 儲存數量：{len(saved_links)}")
    print(f"輸出檔案：{OUTPUT_FILE.resolve()}")
    print(f"HTTP 請求次數：{attempt_counter[0]}")
    print("=" * 65)


if __name__ == "__main__":
    collect_links()
