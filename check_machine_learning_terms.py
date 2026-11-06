import json
import re
from pathlib import Path

# =========================================================
# 設定
# =========================================================

DATABASE_FILES = [
    Path("database/pages_Ａ.json"),
    Path("database/pages_B.json")
]

OUTPUT_DIR = Path("evaluation")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "machine_learning_term_check.json"

# 機器學習及相關名詞
TERMS = [
    "machine learning",
    "machine-learning",
    "machinelearning",
    "deep learning",
    "deep-learning",
    "neural network",
    "neural networks",
    "supervised learning",
    "unsupervised learning",
    "reinforcement learning",
    "training data",
    "model training",
    "model inference",
    "classification",
    "regression",
    "prediction",
    "artificial intelligence",
    "AI",
    "ML"
]

# 要額外列出文章 URL 的名詞
SEARCH_TERMS = [
    "machine learning",
    "neural network",
    "neural networks"
]


# =========================================================
# 讀取資料庫
# =========================================================

def load_documents():

    documents = []

    for file_path in DATABASE_FILES:

        if not file_path.exists():
            print(f"[檔案不存在] {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            records = data

        elif isinstance(data, dict):
            records = data.get("documents", data.get("pages", []))

        else:
            records = []

        documents.extend(records)

        print(f"[讀取成功] {file_path}：{len(records)} 篇")

    return documents


# =========================================================
# 名詞搜尋
# =========================================================

def contains_term(text, term):

    # 忽略大小寫，並將空白、連字號視為可互換
    pattern = re.escape(term.strip())
    pattern = pattern.replace(r"\ ", r"[\s-]+")

    # 避免將較長單字中的部分文字誤判為命中
    regex = re.compile(
        r"(?<![a-zA-Z0-9])" + pattern + r"(?![a-zA-Z0-9])",
        re.IGNORECASE
    )

    return bool(regex.search(text))


# =========================================================
# 檢查所有名詞
# =========================================================

def check_terms(documents):

    results = {}

    for term in TERMS:

        matched_documents = []

        for index, doc in enumerate(documents):

            title = str(doc.get("title", ""))
            content = str(doc.get("text", ""))

            combined_text = title + " " + content

            if contains_term(combined_text, term):

                matched_documents.append({
                    "document_index": index + 1,
                    "title": title,
                    "url": doc.get("url", "")
                })

        results[term] = {
            "document_count": len(matched_documents),
            "documents": matched_documents
        }

    return results


# =========================================================
# 列出指定名詞的文章標題與 URL
# =========================================================

def print_matched_urls(results):

    print("\n" + "=" * 70)
    print("指定名詞命中的文章標題與 URL")
    print("=" * 70)

    for term in SEARCH_TERMS:

        matched_documents = results[term]["documents"]

        print(f"\n【搜尋名詞】{term}")
        print("-" * 70)

        print(f"命中文章數量：{len(matched_documents)} 篇\n")

        if not matched_documents:
            print("沒有找到相關文章。")
            continue

        for index, doc in enumerate(matched_documents, start=1):

            print(f"{index}. {doc['title']}")
            print(f"   URL：{doc['url']}")


# =========================================================
# 主程式
# =========================================================

def main():

    print("=" * 65)
    print("Machine Learning 相關名詞資料庫檢查")
    print("=" * 65)

    documents = load_documents()

    print(f"\n總文件數量：{len(documents)} 篇\n")

    results = check_terms(documents)

    # -----------------------------------------------------
    # 顯示名詞統計
    # -----------------------------------------------------

    print("-" * 65)
    print(f"{'名詞':35s} {'出現文件數量':>12s}")
    print("-" * 65)

    matched_count = 0

    for term, info in results.items():

        count = info["document_count"]

        if count > 0:
            matched_count += 1

        print(f"{term:35s} {count:>10d}")

    print("-" * 65)

    print(f"\n檢查名詞數量：{len(TERMS)}")
    print(f"有出現在資料庫的名詞：{matched_count}")

    # -----------------------------------------------------
    # 列出指定名詞的文章 URL
    # -----------------------------------------------------

    print_matched_urls(results)

    # -----------------------------------------------------
    # 儲存 JSON
    # -----------------------------------------------------

    output_data = {
        "total_documents": len(documents),
        "total_terms": len(TERMS),
        "matched_terms": matched_count,
        "results": results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\n" + "=" * 65)
    print(f"JSON 儲存位置：{OUTPUT_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    main()