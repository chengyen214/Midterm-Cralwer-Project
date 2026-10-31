
import json
import math
from pathlib import Path


# ============================================================
# 1. 路徑設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"

TFIDF_FILE = INDEX_DIR / "tfidf.json"
NORM_FILE = INDEX_DIR / "document_norms.json"


# ============================================================
# 2. 讀取 JSON
# ============================================================

def load_json(file_path):
    """
    讀取 JSON 檔案。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到檔案：{file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# 3. 計算 Document Vector Norm
# ============================================================

def calculate_document_norms(tfidf_data):
    """
    Document Vector Norm：

    ||D|| = sqrt(sum(TFIDF(t,d)^2))

    計算每篇文件的 TF-IDF 向量長度。
    """

    document_norms = {}

    for doc_id, terms in tfidf_data.items():

        squared_sum = 0

        for term, tfidf_value in terms.items():

            squared_sum += tfidf_value ** 2

        norm = math.sqrt(squared_sum)

        document_norms[doc_id] = round(norm, 6)

    return document_norms


# ============================================================
# 4. 儲存 JSON
# ============================================================

def save_json(data, file_path):

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"[儲存完成] {file_path}")


# ============================================================
# 5. 主程式
# ============================================================

def main():

    print("=" * 60)
    print("Document Vector Norm Indexing")
    print("=" * 60)

    # Step 1：讀取 TF-IDF
    print("\n[Step 1] 讀取 TF-IDF")

    tfidf_data = load_json(TFIDF_FILE)

    print(f"文件總數：{len(tfidf_data)}")

    if not tfidf_data:
        print("[錯誤] 沒有 TF-IDF 資料。")
        return

    # Step 2：計算 Document Vector Norm
    print("\n[Step 2] 計算 Document Vector Norm")

    document_norms = calculate_document_norms(
        tfidf_data
    )

    print(f"完成計算：{len(document_norms)} 篇文件")

    # Step 3：儲存結果
    print("\n[Step 3] 儲存 Document Vector Norm")

    save_json(document_norms, NORM_FILE)

    # 顯示部分結果
    print("\n" + "=" * 60)
    print("計算完成")
    print("=" * 60)

    print("\nDocument Vector Norm 範例：")

    for doc_id, norm in list(document_norms.items())[:10]:

        print(f"{doc_id}: {norm}")


if __name__ == "__main__":
    main()
