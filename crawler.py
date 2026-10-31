
# ==================================================
# crawler.py：爬蟲主程式
#
# 做什麼：照著網址清單，一頁一頁下載網頁，
#         只留下標題和文章內容，存成 data/pages_{tag}.json。
#
# 守的規矩：
#   - 同一個網站至少隔 2 秒才抓下一頁（網站要求更久就照網站的）
#   - 網站的 robots.txt 說不准抓的頁面就不抓
#   - 網站回應「太頻繁」或「禁止進入」，就不再抓那個網站
#   - 只抓文章網頁；圖片、PDF、登入頁都跳過
#
# 怎麼執行（要在專案資料夾裡）：
#   python crawler.py filtered_links_part2.json --tag B   （B 部分）
#   python crawler.py filtered_links_part1.json --tag A   （A 部分）
#   已經爬過的不會重爬；確定要重爬，最後加 --overwrite
#
# 產出：
#   data/pages_{tag}.json          爬到的文章
#   logs/crawl_{tag}.log           每次下載的時間紀錄
#   logs/crawl_summary_{tag}.json  統計：成功幾頁、跳過幾頁、原因
# ==================================================

import argparse
import hashlib
import json
import logging
import sys
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

from html_parser import parse_html
from link_collector import matches_target_link
from robots_checker import USER_AGENT, can_fetch, get_crawl_delay


# ==================================================
# 1. 設定
# ==================================================

# 允許爬取的主機（完整 hostname；子網域必須另外列出才會被允許）
ALLOWED_HOSTS = {
    "thenewstack.io",
    "techcrunch.com",
    "spectrum.ieee.org",
    "arstechnica.com",
    "www.infoq.com",
    "www.engadget.com",
    "venturebeat.com",
}

TIMEOUT = 10                         # 單次請求逾時秒數
MAX_ATTEMPTS = 3000                  # 總請求上限（含失敗與重新導向）
MAX_REDIRECTS = 5                    # 單一網址最多跟隨幾次重新導向
MIN_INTERVAL = 2.0                   # 同一主機最少間隔秒數
MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 單頁 HTML 大小上限
MIN_TEXT_WORDS = 30                  # 本文少於此字數視為無效頁面
SAVE_EVERY = 20                      # 每新增幾頁先寫檔一次，避免中斷時全部遺失

REDIRECT_STATUS = {301, 302, 303, 307, 308}
STOP_HOST_STATUS = {429, 503}        # 被限流或伺服器過載：停止爬該主機
MAX_CONSECUTIVE_403 = 3              # 同一主機連續 403 幾次就判定被擋，停止爬

# 路徑中出現這些片段就不下載：登入、帳號、購物車、RSS
SKIP_PATH_SEGMENTS = {
    "login", "signin", "sign-in", "signup", "sign-up", "register",
    "logout", "wp-login.php", "wp-admin", "account", "my-account",
    "cart", "checkout", "feed", "rss",
}

# 下載檔案的副檔名
SKIP_EXTENSIONS = (
    ".pdf", ".zip", ".rar", ".7z", ".gz", ".tar", ".exe", ".dmg",
    ".msi", ".apk", ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".svg", ".mp3", ".mp4", ".mov", ".avi", ".xml", ".json",
    ".csv", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
)

# 本文很短又出現這些字，視為 CAPTCHA / 機器人驗證頁
CAPTCHA_HINTS = (
    "captcha", "are you a robot", "verify you are human",
    "unusual traffic",
)
CAPTCHA_MAX_WORDS = 150

DATA_DIR = Path("data")
LOG_DIR = Path("logs")


# ==================================================
# 2. 執行期狀態
# ==================================================

LAST_REQUEST_TIME = {}       # host → 上一次請求「結束」的時間 (time.monotonic)
HOST_INTERVAL = {}           # host → 實際使用的間隔秒數
STOPPED_HOSTS = {}           # host → 停止原因
CONSECUTIVE_403 = Counter()  # host → 連續 403 次數
VISITED = set()              # 已排入或已請求過的正規化網址
CONTENT_HASHES = {}          # 本文 SHA-1 → 第一次出現的網址（內容去重）
PAGES = []                   # 有效頁面 {url, title, text, fetch_time}
RECORDS = []                 # 每個網址的處理結果，寫進 summary
HOST_STATS = {}              # host → Counter（input_urls/attempts/ok/skip/fail）
STATS = {"attempts": 0}      # 全部 HTTP 請求次數

log = logging.getLogger("crawler")


def host_counter(host):
    return HOST_STATS.setdefault(host, Counter())


# ==================================================
# 3. URL 處理
# ==================================================

def normalize_url(url):
    """
    正規化網址，用來比對是否爬過：
    - scheme 與 hostname 轉小寫，移除預設 Port
    - 空路徑補成 "/"（https://a.com 與 https://a.com/ 是同一頁）
    - 移除 #fragment，保留 query 參數
    不合法或非 HTTP/HTTPS 時回傳 None。
    """
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        host = parts.hostname
        port = parts.port
    except (AttributeError, ValueError):
        return None

    if scheme not in ("http", "https") or not host:
        return None

    if parts.username or parts.password:
        return None

    netloc = host.lower()
    default_port = 80 if scheme == "http" else 443

    if port not in (None, default_port):
        netloc = f"{netloc}:{port}"

    return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))


def in_scope(url):
    """主機必須完全符合 ALLOWED_HOSTS，且符合 link_collector 的網域/路徑規則。"""
    host = urlsplit(url).hostname
    return host in ALLOWED_HOSTS and matches_target_link(url)


def url_skip_reason(url):
    """不用下載就能從網址判斷要跳過的情況，回傳原因；可下載則回傳 None。"""
    path = urlsplit(url).path.lower()

    if path.endswith(SKIP_EXTENSIONS):
        return "download file extension"

    segments = {segment for segment in path.split("/") if segment}

    if segments & SKIP_PATH_SEGMENTS:
        return "login/account/feed url"

    return None


# ==================================================
# 4. 請求間隔
# ==================================================

def get_host_interval(url):
    """間隔秒數 = max(2 秒, robots.txt 的 Crawl-delay)，每個主機只計算一次。"""
    host = urlsplit(url).hostname

    if host not in HOST_INTERVAL:
        crawl_delay = get_crawl_delay(url)
        HOST_INTERVAL[host] = max(MIN_INTERVAL, float(crawl_delay or 0))
        log.info("INTERVAL %s = %.1f s (robots Crawl-delay: %s)",
                 host, HOST_INTERVAL[host], crawl_delay)

    return HOST_INTERVAL[host]


def wait_for_host(url):
    """距離同一主機上一次請求結束還不到間隔秒數時，先等待。"""
    host = urlsplit(url).hostname
    interval = get_host_interval(url)
    previous = LAST_REQUEST_TIME.get(host)

    if previous is not None:
        remaining = interval - (time.monotonic() - previous)

        if remaining > 0:
            time.sleep(remaining)


def next_request_time(host):
    """該主機最早可以再發請求的時間，排程時用來挑下一個主機。"""
    previous = LAST_REQUEST_TIME.get(host)

    if previous is None:
        return 0.0

    return previous + HOST_INTERVAL.get(host, MIN_INTERVAL)


def stop_host(host, reason, retry_after=None):
    """被限流或封鎖時停止爬該主機，之後該主機的網址都記為 skip。"""
    if host in STOPPED_HOSTS:
        return

    STOPPED_HOSTS[host] = reason
    log.warning("STOP HOST %s: %s (Retry-After: %s)", host, reason, retry_after)


# ==================================================
# 5. 下載
# ==================================================

def read_limited(response):
    """分段讀取回應內容，超過 MAX_CONTENT_BYTES 就放棄並回傳 None。"""
    chunks = []
    size = 0

    for chunk in response.iter_content(64 * 1024):
        size += len(chunk)

        if size > MAX_CONTENT_BYTES:
            return None

        chunks.append(chunk)

    return b"".join(chunks)


def send_request(session, url):
    """
    送出一次 GET（不自動跟隨重新導向）。
    請求結束後才記錄時間，確保上一次結束到下一次開始至少間隔指定秒數。

    Returns:
        (status_code, headers, body)
        body 只在 HTTP 200、為 HTML 且不是下載檔時讀取；超過大小上限時為 None。
    """
    host = urlsplit(url).hostname
    wait_for_host(url)

    STATS["attempts"] += 1
    host_counter(host)["attempts"] += 1

    try:
        with session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=True,
        ) as response:
            body = None
            content_type = response.headers.get("Content-Type", "").lower()
            disposition = response.headers.get("Content-Disposition", "").lower()

            # 下載檔（attachment）不讀內容，fetch_page 會記為跳過
            if (
                response.status_code == 200
                and "text/html" in content_type
                and "attachment" not in disposition
            ):
                body = read_limited(response)

            return response.status_code, response.headers, body

    finally:
        LAST_REQUEST_TIME[host] = time.monotonic()


def fetch_page(session, url):
    """
    下載一頁並手動處理重新導向。
    每一跳都重新檢查：請求上限、主機是否已停止、範圍、robots.txt、間隔。

    Returns:
        ("ok", None, 最終網址, HTML bytes)
        ("skip" 或 "fail", 原因, 當時的網址, None)
    """
    current = url

    for hop in range(MAX_REDIRECTS + 1):
        host = urlsplit(current).hostname

        if STATS["attempts"] >= MAX_ATTEMPTS:
            return "skip", "attempt limit reached", current, None

        if host in STOPPED_HOSTS:
            return "skip", "host stopped", current, None

        if not in_scope(current):
            return "skip", "out of scope", current, None

        if not can_fetch(current):
            return "skip", "disallowed by robots.txt", current, None

        # 第一跳已在排程時檢查過網址並加入 VISITED；重新導向後的網址在這裡檢查
        if hop > 0:
            reason = url_skip_reason(current)

            if reason:
                return "skip", reason, current, None

            if current in VISITED:
                return "skip", "duplicate (redirect target already visited)", current, None

            VISITED.add(current)

        try:
            status, headers, body = send_request(session, current)
        except requests.RequestException as exc:
            log.info("GET error %s", current)
            return "fail", f"request error: {type(exc).__name__}", current, None

        # 每次請求都留下時間戳記，可從 log 驗證同一主機的間隔 >= 2 秒
        log.info("GET %s %s", status, current)

        if status in REDIRECT_STATUS:
            location = headers.get("Location")

            if not location:
                return "fail", "redirect without Location", current, None

            next_url = normalize_url(urljoin(current, location))

            if next_url is None:
                return "skip", "invalid redirect url", current, None

            log.info("REDIRECT %s %s -> %s", status, current, next_url)
            current = next_url
            continue

        if status in STOP_HOST_STATUS:
            stop_host(host, f"HTTP {status}", headers.get("Retry-After"))
            return "fail", f"HTTP {status}", current, None

        if status == 403:
            CONSECUTIVE_403[host] += 1

            if CONSECUTIVE_403[host] >= MAX_CONSECUTIVE_403:
                stop_host(host, f"{MAX_CONSECUTIVE_403} consecutive HTTP 403")

            return "fail", "HTTP 403", current, None

        CONSECUTIVE_403[host] = 0

        if status != 200:
            return "fail", f"HTTP {status}", current, None

        if "text/html" not in headers.get("Content-Type", "").lower():
            return "skip", "not HTML", current, None

        if "attachment" in headers.get("Content-Disposition", "").lower():
            return "skip", "download attachment", current, None

        if body is None:
            return "skip", "response too large", current, None

        return "ok", None, current, body

    return "fail", "too many redirects", current, None


# ==================================================
# 6. 解析與驗證
# ==================================================

def looks_like_captcha(parsed):
    """本文很短且出現驗證相關字詞，判定為 CAPTCHA 頁。"""
    if len(parsed["text"].split()) > CAPTCHA_MAX_WORDS:
        return False

    content = f"{parsed['title']} {parsed['text']}".lower()
    return any(hint in content for hint in CAPTCHA_HINTS)


def record(url, outcome, reason=None, detail=None):
    """
    記錄一個網址的最終結果。
    outcome: "ok"（有效頁面）、"skip"（依規則跳過）、"fail"（請求失敗）
    """
    host = urlsplit(url).hostname or "(invalid)"
    host_counter(host)[outcome] += 1

    RECORDS.append({
        "url": url,
        "outcome": outcome,
        "reason": reason,
        "detail": detail,
    })

    suffix = f" ({detail})" if detail else ""

    if outcome == "ok":
        log.info("OK %s%s", url, suffix)
    elif outcome == "skip":
        log.info("SKIP [%s] %s%s", reason, url, suffix)
    else:
        log.warning("FAIL [%s] %s%s", reason, url, suffix)


def crawl_url(session, url):
    """處理清單中的一個網址：下載 → 解析 → 驗證 → 儲存。"""
    outcome, reason, final_url, body = fetch_page(session, url)

    if outcome != "ok":
        record(url, outcome, reason, final_url if final_url != url else None)
        return

    fetch_time = datetime.now().astimezone().isoformat()
    redirected = final_url if final_url != url else None

    parsed = parse_html(body)

    if parsed is None:
        record(url, "skip", "no main text", redirected)
        return

    if parsed["has_password_field"]:
        record(url, "skip", "login page", redirected)
        return

    if looks_like_captcha(parsed):
        record(url, "skip", "captcha page", redirected)
        return

    word_count = len(parsed["text"].split())

    if word_count < MIN_TEXT_WORDS:
        record(url, "skip", "main text too short", f"{word_count} words")
        return

    # 不同網址但本文完全相同（例如只差追蹤參數），只保留第一個
    digest = hashlib.sha1(parsed["text"].encode("utf-8")).hexdigest()

    if digest in CONTENT_HASHES:
        record(url, "skip", "duplicate content", f"same as {CONTENT_HASHES[digest]}")
        return

    CONTENT_HASHES[digest] = final_url

    PAGES.append({
        "url": final_url,
        "title": parsed["title"],
        "text": parsed["text"],
        "fetch_time": fetch_time,
    })

    record(url, "ok", None, redirected)


# ==================================================
# 7. 排程
# ==================================================

def build_queues(urls):
    """
    正規化並去重後，依主機分成多個佇列。
    排程時輪流取不同主機，等待某主機的間隔時可以先處理別的主機。
    """
    queues = {}

    for raw_url in urls:
        url = normalize_url(raw_url) if isinstance(raw_url, str) else None

        if url is None:
            record(str(raw_url), "skip", "invalid url")
            continue

        host = urlsplit(url).hostname
        host_counter(host)["input_urls"] += 1

        if url in VISITED:
            record(url, "skip", "duplicate url")
            continue

        VISITED.add(url)

        reason = url_skip_reason(url)

        if reason:
            record(url, "skip", reason)
            continue

        queues.setdefault(host, deque()).append(url)

    return queues


def run(session, queues, save_path):
    """每次挑「最早可以再發請求」的主機處理下一個網址，直到全部佇列清空。"""
    while True:
        active = [host for host, queue in queues.items() if queue]

        if not active:
            break

        host = min(active, key=next_request_time)
        url = queues[host].popleft()
        before = len(PAGES)

        try:
            crawl_url(session, url)
        except Exception as exc:
            # 單一網址出現意外錯誤時記為失敗，不讓整個爬取中斷、遺失已爬資料
            log.exception("ERROR %s", url)
            record(url, "fail", f"unexpected error: {type(exc).__name__}")

        if len(PAGES) != before and len(PAGES) % SAVE_EVERY == 0:
            save_json(save_path, PAGES)


# ==================================================
# 8. 輸出
# ==================================================

def save_json(path, data):
    """先寫暫存檔再取代，避免寫到一半中斷造成檔案損壞。"""
    temp_path = path.with_name(path.name + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def build_summary(info):
    """整理報告需要的爬取統計。"""
    outcomes = Counter(r["outcome"] for r in RECORDS)
    text_chars = [len(page["text"]) for page in PAGES]
    text_words = [len(page["text"].split()) for page in PAGES]

    def reasons(outcome):
        counter = Counter(r["reason"] for r in RECORDS if r["outcome"] == outcome)
        return dict(counter.most_common())

    return {
        **info,
        "settings": {
            "user_agent": USER_AGENT,
            "allowed_hosts": sorted(ALLOWED_HOSTS),
            "min_interval_seconds": MIN_INTERVAL,
            "host_intervals_used": HOST_INTERVAL,
            "timeout_seconds": TIMEOUT,
            "max_attempts": MAX_ATTEMPTS,
            "max_redirects": MAX_REDIRECTS,
            "min_text_words": MIN_TEXT_WORDS,
        },
        "http_attempts": STATS["attempts"],
        "valid_pages": len(PAGES),
        "failed": outcomes["fail"],
        "skipped": outcomes["skip"],
        "fail_reasons": reasons("fail"),
        "skip_reasons": reasons("skip"),
        "avg_text_chars": round(sum(text_chars) / len(PAGES), 1) if PAGES else 0,
        "avg_text_words": round(sum(text_words) / len(PAGES), 1) if PAGES else 0,
        "total_text_words": sum(text_words),
        "stopped_hosts": STOPPED_HOSTS,
        "per_host": {host: dict(counter) for host, counter in HOST_STATS.items()},
        "failed_urls": [r for r in RECORDS if r["outcome"] == "fail"],
        "skipped_urls": [r for r in RECORDS if r["outcome"] == "skip"],
    }


def setup_logging(log_path):
    """同時輸出到 log 檔與終端機。"""
    log.setLevel(logging.INFO)
    # 時間戳記到毫秒，方便檢查請求間隔
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    for handler in (
        logging.FileHandler(log_path, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ):
        handler.setFormatter(formatter)
        log.addHandler(handler)


# ==================================================
# 9. 主程式
# ==================================================

def main():
    arg_parser = argparse.ArgumentParser(
        description="依網址清單下載網頁，擷取 {url, title, text, fetch_time}",
    )
    arg_parser.add_argument(
        "input",
        nargs="?",
        default="filtered_links_part2.json",
        help="網址清單 JSON（字串陣列），預設 filtered_links_part2.json",
    )
    arg_parser.add_argument(
        "--tag",
        default="B",
        help="輸出檔名後綴（A 或 B 部分），例如 B → data/pages_B.json，預設 B",
    )
    arg_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="已有同一個 tag 的結果時，重新爬取並覆蓋",
    )
    args = arg_parser.parse_args()

    # 先確認清單存在，避免建立空的 log 檔或覆蓋舊結果
    if not Path(args.input).is_file():
        print(f"[ERROR] 找不到網址清單：{args.input}")
        print("請在專案資料夾下指定清單與 tag，例如：")
        print("  python crawler.py filtered_links_part2.json --tag B")
        sys.exit(1)

    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    output_path = DATA_DIR / f"pages_{args.tag}.json"
    log_path = LOG_DIR / f"crawl_{args.tag}.log"
    summary_path = LOG_DIR / f"crawl_summary_{args.tag}.json"

    # 已爬好的結果不小心重跑（例如按 VS Code 的 ▶）會被覆蓋，必須明確加 --overwrite
    if output_path.exists() and not args.overwrite:
        print(f"[STOP] 已經有爬取結果：{output_path}")
        print("重跑會再對網站發送所有請求，並覆蓋舊結果。確定要重爬請加 --overwrite：")
        print(f"  python crawler.py {args.input} --tag {args.tag} --overwrite")
        sys.exit(1)

    setup_logging(log_path)

    with open(args.input, "r", encoding="utf-8") as file:
        urls = json.load(file)

    if not isinstance(urls, list):
        raise ValueError(f"{args.input} 最外層必須是陣列。")

    started_at = datetime.now().astimezone()
    start = time.monotonic()

    log.info("START input=%s urls=%d user_agent=%s", args.input, len(urls), USER_AGENT)

    queues = build_queues(urls)
    log.info("QUEUED %s", {host: len(queue) for host, queue in queues.items()})

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    })

    interrupted = False

    try:
        run(session, queues, output_path)
    except KeyboardInterrupt:
        interrupted = True
        log.warning("INTERRUPTED by user, saving collected pages")
    finally:
        session.close()

    # 中斷時尚未處理的網址也要記錄
    for queue in queues.values():
        for url in queue:
            record(url, "skip", "not processed (interrupted)")

    save_json(output_path, PAGES)

    summary = build_summary({
        "tag": args.tag,
        "input_file": args.input,
        "output_file": str(output_path),
        "log_file": str(log_path),
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now().astimezone().isoformat(),
        "duration_seconds": round(time.monotonic() - start, 1),
        "interrupted": interrupted,
        "input_urls": len(urls),
    })
    save_json(summary_path, summary)

    print("\n" + "=" * 65)
    print("爬取統計")
    print("=" * 65)
    print(f"輸入網址數：{summary['input_urls']}")
    print(f"HTTP 請求次數：{summary['http_attempts']}")
    print(f"有效頁面：{summary['valid_pages']}")
    print(f"失敗：{summary['failed']}  {summary['fail_reasons']}")
    print(f"跳過：{summary['skipped']}  {summary['skip_reasons']}")
    print(f"平均本文長度：{summary['avg_text_words']} 字 / {summary['avg_text_chars']} 字元")
    print(f"停止爬取的主機：{summary['stopped_hosts'] or '無'}")
    print(f"耗時：{summary['duration_seconds']} 秒")
    print(f"資料：{output_path}")
    print(f"Log：{log_path}")
    print(f"統計：{summary_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
