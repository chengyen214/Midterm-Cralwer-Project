
import math
from collections import Counter, defaultdict

from preprocessor import get_preprocessed_documents


# BM25 parameters
K1 = 1.5
B = 0.75


def build_bm25_index():
    """建立 BM25 所需的文件詞頻、DF 與文件長度資料。"""

    documents = get_preprocessed_documents()

    doc_tf = {}
    df = defaultdict(int)
    doc_lengths = {}

    for doc in documents:
        doc_id = str(doc["doc_id"])
        tokens = doc["tokens"]

        term_counts = Counter(tokens)

        doc_tf[doc_id] = dict(term_counts)
        doc_lengths[doc_id] = len(tokens)

        for term in term_counts:
            df[term] += 1

    total_documents = len(documents)

    if total_documents == 0:
        return {
            "doc_tf": {},
            "df": {},
            "idf": {},
            "doc_lengths": {},
            "avgdl": 0,
            "total_documents": 0
        }

    # Calculate BM25 IDF
    idf = {}

    for term, frequency in df.items():
        idf[term] = math.log(
            1 + (total_documents - frequency + 0.5)
            / (frequency + 0.5)
        )

    avgdl = sum(doc_lengths.values()) / total_documents

    return {
        "doc_tf": doc_tf,
        "df": dict(df),
        "idf": idf,
        "doc_lengths": doc_lengths,
        "avgdl": avgdl,
        "total_documents": total_documents
    }


def calculate_bm25_score(query_tokens, doc_id, bm25_index):
    """計算單一文件的 BM25 分數。"""

    doc_tf = bm25_index["doc_tf"]
    idf = bm25_index["idf"]
    doc_lengths = bm25_index["doc_lengths"]
    avgdl = bm25_index["avgdl"]

    if avgdl == 0:
        return 0.0

    term_counts = doc_tf.get(str(doc_id), {})
    doc_length = doc_lengths.get(str(doc_id), 0)

    score = 0.0

    for term in query_tokens:

        if term not in term_counts or term not in idf:
            continue

        tf = term_counts[term]

        numerator = tf * (K1 + 1)

        denominator = (
            tf
            + K1 * (
                1 - B
                + B * doc_length / avgdl
            )
        )

        score += idf[term] * numerator / denominator

    return score


def bm25_search(query, document_info, bm25_index, top_k=10):
    """執行 BM25 搜尋並回傳 Top K 結果。"""

    from preprocessor import preprocess_text

    query_tokens = preprocess_text(query)

    if not query_tokens:
        return {
            "total_results": 0,
            "results": []
        }

    results = []

    # Only score documents containing at least one query term
    candidate_docs = set()

    for term in query_tokens:
        for doc_id, terms in bm25_index["doc_tf"].items():
            if term in terms:
                candidate_docs.add(doc_id)

    for doc_id in candidate_docs:

        score = calculate_bm25_score(
            query_tokens,
            doc_id,
            bm25_index
        )

        if score > 0 and doc_id in document_info:

            info = document_info[doc_id]

            results.append({
                "title": info["title"],
                "url": info["url"],
                "snippet": generate_snippet(info["text"]),
                "score": score
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return {
        "total_results": len(results),
        "results": results[:top_k]
    }


def generate_snippet(text):
    """產生搜尋結果摘要。"""

    import re
    from html import unescape

    if not isinstance(text, str):
        return ""

    text = unescape(re.sub(r"<[^>]*>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()

    words = re.findall(
        r"\b[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*\b",
        text
    )

    if words:
        return " ".join(words[:75]) + (
            "..." if len(words) > 75 else ""
        )

    return text[:120] + ("..." if len(text) > 120 else "")
