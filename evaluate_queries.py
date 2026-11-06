import json
import os
import time
from datetime import datetime

import matplotlib.pyplot as plt

from search import load_index, search


# ============================================================
# 1. 設定測試 Query
# ============================================================

QUERIES = [
    "Gemini Oct",
    "AI",
    "Google AI",
    "OpenAI",
    "ChatGPT updates",
    "NVIDIA AI chips",
    "machine learning",
    "autonomous vehicles",
    "cybersecurity attacks",
    "Apple Intelligence"
]

TOP_K = 5

OUTPUT_DIR = "evaluation"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "query_top5.json")
CHART_FILE = os.path.join(OUTPUT_DIR, "query_time.png")


# ============================================================
# 2. 載入索引
# ============================================================

print("=" * 65)
print("搜尋引擎 Query 測試")
print("=" * 65)

print("\n[1] 載入搜尋索引中...")

index_data = load_index()

print("[完成] 搜尋索引載入成功")


# ============================================================
# 3. 執行 Query 並測量檢索時間
# ============================================================

all_results = []
query_times = []

for query_number, query in enumerate(QUERIES, start=1):

    print("\n" + "=" * 65)
    print(f"Query {query_number:02d}: {query}")
    print("=" * 65)

    # --------------------------------------------------------
    # Timing Boundary START
    # 只測量 search() 的執行時間
    # --------------------------------------------------------

    start_time = time.perf_counter()

    results = search(
        query=query,
        index_data=index_data,
        top_k=TOP_K
    )

    end_time = time.perf_counter()

    # --------------------------------------------------------
    # Timing Boundary END
    # --------------------------------------------------------

    query_time_ms = (end_time - start_time) * 1000

    query_times.append(query_time_ms)

    print(f"Query 檢索時間：{query_time_ms:.4f} ms")

    # search() 回傳 Dictionary 時，取出搜尋結果
    if isinstance(results, dict):
        results = results.get("results", [])

    top5 = []

    for rank, result in enumerate(results[:TOP_K], start=1):

        # 透過 URL 找到原始文章內容
        url = result.get("url", "")

        document_context = ""

        for doc in index_data[4].values():
            if doc.get("url") == url:
                document_context = doc.get("text", "")
                break

        item = {
            "rank": rank,
            "title": result.get("title", ""),
            "url": url,
            "context": document_context,
            "score": result.get("score", 0),
            "relevance": None
        }

        top5.append(item)

        print(f"\nRank {rank}")
        print(f"Title: {item['title']}")
        print(f"URL: {item['url']}")
        print(f"Score: {item['score']:.6f}")
        print(f"Context 長度：{len(item['context'])} 字元")

    # 將 Query、Top 5 與檢索時間一起保存
    all_results.append({
        "query_id": f"Q{query_number:02d}",
        "query": query,
        "result_count": len(top5),
        "query_time_ms": round(query_time_ms, 4),
        "top5": top5
    })


# ============================================================
# 4. 儲存 JSON
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

output_data = {
    "search_method": "TF-IDF",
    "top_k": TOP_K,
    "total_queries": len(QUERIES),
    "timing_boundary": "search() function execution only",
    "generated_at": datetime.now().isoformat(
        timespec="seconds"
    ),
    "queries": all_results
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        output_data,
        file,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# 5. 執行結果統計
# ============================================================

total_results = sum(
    item["result_count"] for item in all_results
)

avg_time = sum(query_times) / len(query_times)
min_time = min(query_times)
max_time = max(query_times)
total_time = sum(query_times)

print("\n" + "=" * 65)
print("搜尋結果統計")
print("=" * 65)

print(f"Query 數量：{len(QUERIES)}")
print(f"預期搜尋結果：{len(QUERIES) * TOP_K}")
print(f"實際搜尋結果：{total_results}")

print("\n各 Query 搜尋結果數量：")

for item in all_results:
    print(
        f"{item['query_id']} | "
        f"{item['query']:<25} | "
        f"Top 5：{item['result_count']} 筆"
    )


# ============================================================
# 6. Query 檢索時間統計
# ============================================================

print("\n" + "=" * 65)
print("Query Retrieval Latency 統計")
print("=" * 65)

print(f"平均檢索時間：{avg_time:.4f} ms")
print(f"最快檢索時間：{min_time:.4f} ms")
print(f"最慢檢索時間：{max_time:.4f} ms")
print(f"總檢索時間：{total_time:.4f} ms")

print("\n各 Query 檢索時間：")

for item in all_results:
    print(
        f"{item['query_id']} | "
        f"{item['query']:<25} | "
        f"{item['query_time_ms']:.4f} ms"
    )


# ============================================================
# 7. 繪製 Query 檢索時間長條圖
# ============================================================

query_labels = [
    item["query_id"] for item in all_results
]

plt.figure(figsize=(12, 6))

bars = plt.bar(
    query_labels,
    query_times
)

plt.title("Query Retrieval Latency (TF-IDF)")
plt.xlabel("Query ID")
plt.ylabel("Retrieval Time (ms)")

plt.xticks(rotation=0)

# 在長條上方顯示時間
for bar, value in zip(bars, query_times):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.2f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()

plt.savefig(CHART_FILE, dpi=300)

plt.show()


# ============================================================
# 8. 完成
# ============================================================

print("\n" + "=" * 65)
print("測試完成")
print("=" * 65)

print(f"Query 數量：{len(QUERIES)}")
print(f"平均檢索時間：{avg_time:.4f} ms")
print(f"JSON 儲存位置：{OUTPUT_FILE}")
print(f"檢索時間圖表：{CHART_FILE}")

print("\n[完成] Top 5 搜尋結果與 Query 檢索時間已儲存")