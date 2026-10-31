
import math
import json
from collections import Counter, defaultdict
from pathlib import Path

from preprocessor import get_preprocessed_documents


# ============================================================
# 1. 路徑設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "index"

TF_FILE = OUTPUT_DIR / "tf.json"
DF_FILE = OUTPUT_DIR / "df.json"
IDF_FILE = OUTPUT_DIR / "idf.json"
TFIDF_FILE = OUTPUT_DIR / "tfidf.json"


# ============================================================
# 2. 計算 TF：Log Frequency Weighting
# ============================================================

def calculate_tf(documents):
    """
    TF(t,d) = 1 + log10(f_t,d)

    如果詞彙沒有出現，TF = 0。
    """

    tf_data = {}

    for document in documents:

        doc_id = document["doc_id"]
        tokens = document["tokens"]

        # 統計每個詞彙在文件中的出現次數
        term_counts = Counter(tokens)

        tf_data[doc_id] = {}

        for term, frequency in term_counts.items():

            if frequency > 0:
                tf_value = 1 + math.log10(frequency)
            else:
                tf_value = 0

            tf_data[doc_id][term] = round(tf_value, 6)

    return tf_data


# ============================================================
# 3. 計算 DF：Document Frequency
# ============================================================

def calculate_df(documents):
    """
    DF(t) = 包含詞彙 t 的不同文件數量。
    """

    df_data = defaultdict(int)

    for document in documents:

        tokens = document["tokens"]

        # set 確保同一篇文件的詞彙只計算一次
        unique_terms = set(tokens)

        for term in unique_terms:
            df_data[term] += 1

    return dict(df_data)


# ============================================================
# 4. 計算 IDF：Smoothed IDF
# ============================================================

def calculate_idf(df_data, total_documents):
    """
    IDF(t) = 1 + ln((N + 1) / (DF(t) + 1))
    """

    idf_data = {}

    for term, df_value in df_data.items():

        idf_value = 1 + math.log(
            (total_documents + 1) / (df_value + 1)
        )

        idf_data[term] = round(idf_value, 6)

    return idf_data


# ============================================================
# 5. 計算 TF-IDF
# ============================================================

def calculate_tfidf(tf_data, idf_data):
    """
    TF-IDF(t,d) = TF(t,d) * IDF(t)
    """

    tfidf_data = {}

    for doc_id, terms in tf_data.items():

        tfidf_data[doc_id] = {}

        for term, tf_value in terms.items():

            idf_value = idf_data[term]

            tfidf_value = tf_value * idf_value

            tfidf_data[doc_id][term] = round(
                tfidf_value, 6
            )

    return tfidf_data


# ============================================================
# 6. 儲存 JSON
# ============================================================

def save_json(data, file_path):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"[儲存完成] {file_path}")


# ============================================================
# 7. 主程式
# ============================================================

def main():

    print("=" * 60)
    print("TF → DF → IDF → TF-IDF")
    print("=" * 60)

    # 呼叫前處理程式
    documents = get_preprocessed_documents()

    total_documents = len(documents)

    print(f"\n文件總數 N：{total_documents}")

    if total_documents == 0:
        print("[錯誤] 沒有可供計算的文件。")
        return

    # Step 1：計算 TF
    print("\n[Step 1] 計算 TF")
    tf_data = calculate_tf(documents)
    print(f"TF 文件數：{len(tf_data)}")

    # Step 2：計算 DF
    print("\n[Step 2] 計算 DF")
    df_data = calculate_df(documents)
    print(f"DF 詞彙數：{len(df_data)}")

    # Step 3：計算 IDF
    print("\n[Step 3] 計算 IDF")
    idf_data = calculate_idf(df_data, total_documents)
    print(f"IDF 詞彙數：{len(idf_data)}")

    # Step 4：計算 TF-IDF
    print("\n[Step 4] 計算 TF-IDF")
    tfidf_data = calculate_tfidf(tf_data, idf_data)

    # 儲存計算結果
    save_json(tf_data, TF_FILE)
    save_json(df_data, DF_FILE)
    save_json(idf_data, IDF_FILE)
    save_json(tfidf_data, TFIDF_FILE)

    # 顯示部分結果
    print("\n" + "=" * 60)
    print("計算完成")
    print("=" * 60)

    first_doc_id = next(iter(tf_data))

    print(f"\n範例文件：{first_doc_id}")

    print("\nTF：")
    for term, value in list(tf_data[first_doc_id].items())[:10]:
        print(f"{term}: {value}")

    print("\nDF / IDF：")
    for term in list(df_data.keys())[:10]:
        print(
            f"{term}: DF={df_data[term]}, "
            f"IDF={idf_data[term]}"
        )

    print("\nTF-IDF：")
    for term, value in list(tfidf_data[first_doc_id].items())[:10]:
        print(f"{term}: {value}")


if __name__ == "__main__":
    main()
