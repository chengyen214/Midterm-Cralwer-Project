
import json
import math
import re
from collections import Counter
from pathlib import Path

from preprocessor import (
    preprocess_text,
    get_preprocessed_documents
)

# ============================================================
# 路徑設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INDEX_DIR = BASE_DIR / "index"
DATABASE_DIR = BASE_DIR / "database"

TFIDF_FILE = INDEX_DIR / "tfidf.json"
IDF_FILE = INDEX_DIR / "idf.json"
POSTINGS_FILE = INDEX_DIR / "postings.json"
NORM_FILE = INDEX_DIR / "document_norms.json"

RAW_FILES = [
    DATABASE_DIR / "pages_Ａ.json",
    DATABASE_DIR / "pages_B.json"
]


# ============================================================
# JSON 載入
# ============================================================

def load_json(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到檔案：{file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# 載入原始文章
# 從 pages_Ａ.json 和 pages_B.json 取得 text
# ============================================================

def load_original_documents():

    documents = {}

    for file_path in RAW_FILES:

        if not file_path.exists():
            raise FileNotFoundError(
                f"找不到原始資料：{file_path}"
            )

        data = load_json(file_path)

        for doc in data:

            url = doc.get("url", "").strip()

            if not url:
                continue

            documents[url] = {
                "title": doc.get("title", ""),
                "url": url,
                "text": doc.get("text", "")
            }

    print(f"原始文章載入數量：{len(documents)}")

    return documents


# ============================================================
# 載入搜尋所需資料
# ============================================================

def load_index():

    print("正在載入搜尋索引...")

    tfidf_data = load_json(TFIDF_FILE)
    idf_data = load_json(IDF_FILE)
    postings_data = load_json(POSTINGS_FILE)
    document_norms = load_json(NORM_FILE)

    # 從原始 JSON 載入文章資訊
    original_documents = load_original_documents()

    # 建立 DocID 對應的文章資訊
    documents = get_preprocessed_documents()

    document_info = {}

    for doc in documents:

        doc_id = doc["doc_id"]
        url = doc.get("url", "")

        # 使用 URL 找到原始文章
        original_doc = original_documents.get(url, {})

        document_info[doc_id] = {
            "title": original_doc.get(
                "title",
                doc.get("title", "")
            ),
            "url": url,
            "text": original_doc.get("text", "")
        }

    print(f"索引文件數量：{len(tfidf_data)}")
    print("索引載入完成！")

    return (
        tfidf_data,
        idf_data,
        postings_data,
        document_norms,
        document_info
    )


# ============================================================
# Query TF
# 使用 Log Frequency Weighting
# TF(t,q) = 1 + log10(frequency)
# ============================================================

def calculate_query_tf(tokens):

    frequency = Counter(tokens)

    query_tf = {}

    for term, count in frequency.items():

        if count > 0:
            query_tf[term] = 1 + math.log10(count)

    return query_tf


# ============================================================
# Query TF-IDF
# 使用索引建立時儲存的 IDF
# ============================================================

def calculate_query_tfidf(query_tf, idf_data):

    query_tfidf = {}

    for term, tf_value in query_tf.items():

        if term not in idf_data:
            continue

        query_tfidf[term] = (
            tf_value * idf_data[term]
        )

    return query_tfidf


# ============================================================
# Query Vector Norm
# ||Q|| = sqrt(sum(TFIDF(t,q)^2))
# ============================================================

def calculate_query_norm(query_tfidf):

    squared_sum = sum(
        value ** 2
        for value in query_tfidf.values()
    )

    return math.sqrt(squared_sum)


# ============================================================
# 從 Inverted Index 找出候選文件
# ============================================================

def find_candidate_documents(query_tfidf, postings_data):

    candidate_documents = set()

    for term in query_tfidf:

        if term not in postings_data:
            continue

        for posting in postings_data[term]:

            doc_id = posting[0]

            candidate_documents.add(doc_id)

    return candidate_documents


# ============================================================
# Cosine Similarity
# Similarity(Q,D) = (Q · D) / (||Q|| * ||D||)
# ============================================================

def calculate_cosine_similarity(
    query_tfidf,
    document_tfidf,
    query_norm,
    document_norm
):

    if query_norm == 0 or document_norm == 0:
        return 0

    dot_product = 0

    for term, query_weight in query_tfidf.items():

        document_weight = document_tfidf.get(term, 0)

        dot_product += (
            query_weight * document_weight
        )

    similarity = dot_product / (
        query_norm * document_norm
    )

    return similarity


# ============================================================
# 產生 Snippet
# 英文：約 50–100 個單字
# 中文：約 80–150 個中文字
# 從原始文章 text 擷取
# ============================================================

def generate_snippet(text):

    if not isinstance(text, str):
        return ""

    # 移除 HTML 標籤
    text = re.sub(r"<[^>]*>", " ", text)

    # 移除 HTML 常見空白及多餘空格
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    # 判斷是否包含中文字
    has_chinese = any(
        "\u4e00" <= char <= "\u9fff"
        for char in text
    )

    # --------------------------------------------------------
    # 中文 Snippet：擷取 120 個中文字
    # --------------------------------------------------------

    if has_chinese:

        result = []
        chinese_count = 0

        for char in text:

            result.append(char)

            if "\u4e00" <= char <= "\u9fff":
                chinese_count += 1

            if chinese_count >= 120:
                break

        snippet = "".join(result).strip()

        if len(text) > len(snippet):
            snippet += "..."

        return snippet

    # --------------------------------------------------------
    # 英文 Snippet：擷取前 75 個英文單字
    # --------------------------------------------------------

    words = re.findall(
        r"\b[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*\b",
        text
    )

    if not words:
        return ""

    if len(words) <= 100:
        return text

    return " ".join(words[:75]) + "..."


# ============================================================
# 搜尋主程式
# ============================================================

def search(
    query,
    index_data,
    top_k=10
):

    (
        tfidf_data,
        idf_data,
        postings_data,
        document_norms,
        document_info
    ) = index_data

    # --------------------------------------------------------
    # 1. Query Preprocessing
    # --------------------------------------------------------

    query_tokens = preprocess_text(query)

    if not query_tokens:

        return {
            "query": query,
            "total_indexed_pages": len(tfidf_data),
            "total_results": 0,
            "results": []
        }

    # --------------------------------------------------------
    # 2. Query TF
    # --------------------------------------------------------

    query_tf = calculate_query_tf(query_tokens)

    # --------------------------------------------------------
    # 3. Query TF-IDF
    # --------------------------------------------------------

    query_tfidf = calculate_query_tfidf(
        query_tf,
        idf_data
    )

    if not query_tfidf:

        return {
            "query": query,
            "total_indexed_pages": len(tfidf_data),
            "total_results": 0,
            "results": []
        }

    # --------------------------------------------------------
    # 4. Query Vector Norm
    # --------------------------------------------------------

    query_norm = calculate_query_norm(query_tfidf)

    if query_norm == 0:

        return {
            "query": query,
            "total_indexed_pages": len(tfidf_data),
            "total_results": 0,
            "results": []
        }

    # --------------------------------------------------------
    # 5. Inverted Index
    # 找出包含任一查詢詞的文件
    # --------------------------------------------------------

    candidate_documents = find_candidate_documents(
        query_tfidf,
        postings_data
    )

    # --------------------------------------------------------
    # 6. Cosine Similarity
    # --------------------------------------------------------

    results = []

    for doc_id in candidate_documents:

        if doc_id not in tfidf_data:
            continue

        if doc_id not in document_norms:
            continue

        document_tfidf = tfidf_data[doc_id]

        document_norm = document_norms[doc_id]

        score = calculate_cosine_similarity(
            query_tfidf,
            document_tfidf,
            query_norm,
            document_norm
        )

        if score <= 0:
            continue

        info = document_info.get(doc_id, {})

        results.append({
            "title": info.get("title", ""),
            "url": info.get("url", ""),
            "snippet": generate_snippet(
                info.get("text", "")
            ),
            "score": round(score, 6)
        })

    # --------------------------------------------------------
    # 7. 排序並取得 Top-K
    # --------------------------------------------------------

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    results = results[:top_k]

    # --------------------------------------------------------
    # 8. 回傳給前端
    # --------------------------------------------------------

    response = {
        "query": query,
        "total_indexed_pages": len(tfidf_data),
        "total_results": len(results),
        "results": results
    }

    return response


# ============================================================
# Command Line Interface
# ============================================================

def main():

    print("=" * 60)
    print("Technology News Search Engine")
    print("=" * 60)

    index_data = load_index()

    total_pages = len(index_data[0])

    print(f"\n總索引頁數：{total_pages}")
    print("輸入 q 離開搜尋系統。")

    while True:

        print("\n" + "-" * 60)

        query = input("請輸入搜尋內容：").strip()

        if query.lower() == "q":
            print("結束搜尋系統。")
            break

        if not query:
            print("請輸入搜尋內容。")
            continue

        response = search(
            query,
            index_data,
            top_k=10
        )

        print("\n搜尋結果")
        print("=" * 60)

        print(
            f"總索引頁數："
            f"{response['total_indexed_pages']}"
        )

        print(
            f"搜尋結果數量："
            f"{response['total_results']}"
        )

        if not response["results"]:
            print("找不到符合條件的搜尋結果。")
            continue

        for i, result in enumerate(
            response["results"],
            start=1
        ):

            print(f"\n[{i}] {result['title']}")

            print(f"URL：{result['url']}")

            print(f"Snippet：{result['snippet']}")

            print(f"Score：{result['score']}")


if __name__ == "__main__":
    main()
