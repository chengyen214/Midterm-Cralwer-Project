
import json
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

import matplotlib.pyplot as plt

# ==============================
# 基本設定
# ==============================

FILES = [
    Path("database/pages_Ａ.json"),
    Path("database/pages_B.json")
]

OUTPUT_DIR = Path("crawler_statistics")
OUTPUT_DIR.mkdir(exist_ok=True)

# 中文字型
plt.rcParams["font.sans-serif"] = [
    "Microsoft JhengHei",
    "SimHei",
    "Noto Sans CJK TC"
]
plt.rcParams["axes.unicode_minus"] = False


# ==============================
# 讀取資料
# ==============================

def load_articles():
    articles = []

    for file_path in FILES:
        if not file_path.exists():
            print(f"[WARNING] 找不到檔案：{file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        print(f"[讀取成功] {file_path.name}：{len(data)} 篇")
        articles.extend(data)

    return articles


# ==============================
# 統計資料
# ==============================

def calculate_statistics(articles):

    website_counts = Counter()
    urls = []

    missing_url = 0
    missing_title = 0
    missing_text = 0
    valid_articles = 0

    for article in articles:

        url = (article.get("url") or "").strip()
        title = (article.get("title") or "").strip()
        text = (article.get("text") or "").strip()

        if url:
            domain = urlparse(url).netloc.lower()
            website_counts[domain] += 1
            urls.append(url)
        else:
            missing_url += 1

        if not title:
            missing_title += 1

        if not text:
            missing_text += 1

        if url and title and text:
            valid_articles += 1

    duplicate_urls = len(urls) - len(set(urls))

    statistics = {
        "total": len(articles),
        "valid": valid_articles,
        "missing_url": missing_url,
        "missing_title": missing_title,
        "missing_text": missing_text,
        "duplicate_urls": duplicate_urls
    }

    return website_counts, statistics


# ==============================
# 圖表 1：各網站文章數量
# ==============================

def plot_website_bar(website_counts):

    domains = list(website_counts.keys())
    counts = list(website_counts.values())

    plt.figure(figsize=(12, 6))
    bars = plt.bar(domains, counts)

    plt.title("Article Count by Website", fontsize=16)
    plt.xlabel("Website")
    plt.ylabel("Number of Articles")
    plt.xticks(rotation=35, ha="right")

    for bar, count in zip(bars, counts):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(count),
            ha="center",
            va="bottom"
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_website_article_count.png", dpi=300)
    plt.close()


# ==============================
# 圖表 2：各網站文章比例
# ==============================

def plot_website_pie(website_counts):

    plt.figure(figsize=(9, 7))

    plt.pie(
        website_counts.values(),
        labels=website_counts.keys(),
        autopct="%1.1f%%",
        startangle=90
    )

    plt.title("Article Source Distribution", fontsize=16)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_website_distribution.png", dpi=300)
    plt.close()


# ==============================
# 圖表 3：文章資料品質
# ==============================

def plot_data_quality(statistics):

    labels = [
        "Valid Articles",
        "Missing URL",
        "Missing Title",
        "Missing Text",
        "Duplicate URLs"
    ]

    values = [
        statistics["valid"],
        statistics["missing_url"],
        statistics["missing_title"],
        statistics["missing_text"],
        statistics["duplicate_urls"]
    ]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, values)

    plt.title("Article Data Quality Statistics", fontsize=16)
    plt.xlabel("Data Quality")
    plt.ylabel("Number of Articles")
    plt.xticks(rotation=20, ha="right")

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(value),
            ha="center",
            va="bottom"
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_data_quality.png", dpi=300)
    plt.close()


# ==============================
# 圖表 4：文件處理數量
# ==============================

def plot_document_comparison(statistics):

    # 這裡讀取前處理後的文件數量
    from preprocessor import get_preprocessed_documents

    documents = get_preprocessed_documents()
    indexed_count = len(documents)

    labels = [
        "Raw Articles",
        "Valid Articles",
        "Indexed Documents"
    ]

    values = [
        statistics["total"],
        statistics["valid"],
        indexed_count
    ]

    plt.figure(figsize=(9, 6))
    bars = plt.bar(labels, values)

    plt.title("Document Processing Statistics", fontsize=16)
    plt.ylabel("Number of Documents")

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(value),
            ha="center",
            va="bottom"
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_document_comparison.png", dpi=300)
    plt.close()

    return indexed_count


# ==============================
# 主程式
# ==============================

def main():

    print("=" * 60)
    print("Web Search Engine - Crawler Statistics")
    print("=" * 60)

    articles = load_articles()

    website_counts, statistics = calculate_statistics(articles)

    indexed_count = plot_document_comparison(statistics)

    plot_website_bar(website_counts)
    plot_website_pie(website_counts)
    plot_data_quality(statistics)

    print("\n[爬蟲統計結果]")
    print("-" * 60)

    for key, value in statistics.items():
        print(f"{key}: {value}")

    print(f"Indexed Documents: {indexed_count}")

    print("\n[各網站文章數量]")
    for domain, count in website_counts.most_common():
        print(f"{domain}: {count}")

    print("\n[圖表產生完成]")
    print(f"儲存位置：{OUTPUT_DIR.resolve()}")

    print("=" * 60)


if __name__ == "__main__":
    main()
