import json
import math
from pathlib import Path
from collections import Counter

from preprocessor import preprocess_text, get_preprocessed_documents


# =====================================================
# 1. 設定
# =====================================================

TARGET_URL = "https://thenewstack.io/python/"

RAW_FILES = [
    Path("database/pages_Ａ.json"),
    Path("database/pages_B.json")
]

INDEX_DIR = Path("index")

TOLERANCE = 1e-6


# =====================================================
# 2. 讀取 JSON
# =====================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_content(record):
    """取得 JSON 中實際儲存的文章內容。"""

    for field in ["text", "content", "con"]:
        value = record.get(field)

        if isinstance(value, str) and value.strip():
            return value

    return ""


def normalize_url(url):
    return (url or "").strip().rstrip("/")


# =====================================================
# 3. 使用 URL 找出原始儲存內容
# =====================================================

print("=" * 80)
print("Python Archives：使用儲存內容重新計算 TF-IDF")
print("=" * 80)

raw_records = []

for path in RAW_FILES:

    if not path.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")

    data = load_json(path)

    if not isinstance(data, list):
        raise ValueError(f"{path} 的 JSON 最外層不是 list，請確認資料格式。")

    raw_records.extend(data)

target_record = None

for record in raw_records:

    if normalize_url(record.get("url")) == normalize_url(TARGET_URL):
        target_record = record
        break

if target_record is None:
    raise ValueError("兩份 JSON 都找不到指定 URL。")

target_content = get_content(target_record)

if not target_content:
    raise ValueError("找到 URL，但沒有可用的 text/content/con 內容。")

print("\n【1. 找到儲存的文章】")
print("URL：", target_record.get("url"))
print("Title：", target_record.get("title"))
print("內容長度：", len(target_content), "字元")

print("\n儲存內容前 500 字：")
print(target_content[:500])


# =====================================================
# 4. 建立 URL 對應原始儲存內容
# =====================================================

raw_content_map = {}

for record in raw_records:

    url = normalize_url(record.get("url"))

    if not url:
        continue

    content = get_content(record)

    if content and url not in raw_content_map:
        raw_content_map[url] = content


# =====================================================
# 5. 取得原本文件 DocID 順序
#    使用現有前處理結果確認文件集合及 DocID
# =====================================================

processed_documents = get_preprocessed_documents()

doc_id_map = {
    normalize_url(doc["url"]): doc["doc_id"]
    for doc in processed_documents
}

target_url_normalized = normalize_url(TARGET_URL)

if target_url_normalized not in doc_id_map:
    raise ValueError("指定 URL 不在目前的前處理文件中。")

target_doc_id = doc_id_map[target_url_normalized]

print("\n【2. 文件資訊】")
print("DocID：", target_doc_id)
print("前處理文件總數：", len(processed_documents))


# =====================================================
# 6. 使用 JSON 儲存內容重新前處理整份語料
# =====================================================

corpus_tokens = {}
target_tokens = None

for doc in processed_documents:

    url = normalize_url(doc["url"])

    if url not in raw_content_map:
        continue

    # 重新使用儲存的文章內容進行前處理
    tokens = preprocess_text(raw_content_map[url])

    if not tokens:
        continue

    corpus_tokens[doc["doc_id"]] = tokens

    if url == target_url_normalized:
        target_tokens = tokens

if target_tokens is None:
    raise ValueError("無法從儲存內容重新取得目標文章 tokens。")

N = len(corpus_tokens)

print("\n【3. 重新前處理結果】")
print("重新計算的文件數量 N：", N)
print("目標文件 Token 數量：", len(target_tokens))
print("目標文件不同詞彙數量：", len(set(target_tokens)))


# =====================================================
# 7. 重新計算整份語料 DF
# =====================================================

df_counter = Counter()

for tokens in corpus_tokens.values():

    for term in set(tokens):
        df_counter[term] += 1


# =====================================================
# 8. 重新計算目標文件 TF、IDF、TF-IDF
# =====================================================

target_counter = Counter(target_tokens)

expected_tf = {}
expected_idf = {}
expected_tfidf = {}

for term, frequency in target_counter.items():

    # TF = 1 + log10(frequency)
    tf = 1 + math.log10(frequency)

    # DF = 該詞出現的文件數
    df = df_counter[term]

    # IDF = 1 + ln((N+1)/(DF+1))
    idf = 1 + math.log((N + 1) / (df + 1))

    # TF-IDF = TF * IDF
    tfidf = tf * idf

    expected_tf[term] = tf
    expected_idf[term] = idf
    expected_tfidf[term] = tfidf


# =====================================================
# 9. 讀取既有索引進行比對
# =====================================================

def load_index(filename):
    path = INDEX_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"找不到索引：{path}")

    return load_json(path)


saved_tf = load_index("tf.json")
saved_df = load_index("df.json")
saved_idf = load_index("idf.json")
saved_tfidf = load_index("tfidf.json")
saved_norms = load_index("document_norms.json")

actual_tf = saved_tf.get(target_doc_id, {})
actual_tfidf = saved_tfidf.get(target_doc_id, {})


# =====================================================
# 10. 顯示逐詞重新計算結果
# =====================================================

print("\n【4. TF / DF / IDF / TF-IDF 重新計算】")
print("DocID：", target_doc_id)
print("-" * 125)

print(
    f"{'Term':<25}"
    f"{'Freq':>7}"
    f"{'TF':>12}"
    f"{'DF':>9}"
    f"{'IDF':>12}"
    f"{'TF-IDF':>14}"
    f"{'原索引TF-IDF':>17}"
    f"{'結果':>10}"
)

print("-" * 125)

all_pass = True

for term in sorted(target_counter):

    frequency = target_counter[term]

    tf = expected_tf[term]
    df = df_counter[term]
    idf = expected_idf[term]
    tfidf = expected_tfidf[term]

    old_tfidf = actual_tfidf.get(term)

    passed = (
        math.isclose(
            tf, actual_tf.get(term, float("nan")),
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE
        )
        and saved_df.get(term) == df
        and math.isclose(
            idf, saved_idf.get(term, float("nan")),
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE
        )
        and isinstance(old_tfidf, (int, float))
        and math.isclose(
            tfidf, old_tfidf,
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE
        )
    )

    if not passed:
        all_pass = False

    old_value = (
        f"{old_tfidf:.6f}"
        if isinstance(old_tfidf, (int, float))
        else "MISSING"
    )

    print(
        f"{term:<25}"
        f"{frequency:>7}"
        f"{tf:>12.6f}"
        f"{df:>9}"
        f"{idf:>12.6f}"
        f"{tfidf:>14.6f}"
        f"{old_value:>17}"
        f"{'PASS' if passed else 'FAIL':>10}"
    )


# =====================================================
# 11. 重新計算 Document Norm
# =====================================================

print("\n【5. Document Norm】")

expected_norm = math.sqrt(
    sum(weight ** 2 for weight in expected_tfidf.values())
)

actual_norm = saved_norms.get(target_doc_id)

norm_pass = (
    isinstance(actual_norm, (int, float))
    and math.isclose(
        expected_norm,
        actual_norm,
        rel_tol=TOLERANCE,
        abs_tol=TOLERANCE
    )
)

print(f"重新計算 Norm：{expected_norm:.8f}")
print(f"原索引 Norm：{actual_norm}")
print("檢查結果：", "PASS" if norm_pass else "FAIL")

if not norm_pass:
    all_pass = False


# =====================================================
# 12. 最終結果
# =====================================================

print("\n" + "=" * 80)
print("最終檢查結果")
print("=" * 80)

print("URL：", TARGET_URL)
print("DocID：", target_doc_id)
print("重新計算文件數量：", N)
print("目標文件詞彙數量：", len(target_counter))

if all_pass:
    print("\n[PASS] 儲存內容重新計算結果與原索引一致。")
else:
    print("\n[FAIL] 重新計算結果與原索引有差異，請檢查前處理及索引。")

print("=" * 80)