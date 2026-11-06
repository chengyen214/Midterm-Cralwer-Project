import math

from search import (
    load_index,
    search,
    calculate_query_tf,
    calculate_query_tfidf,
    calculate_query_norm
)

from preprocessor import preprocess_text


TARGET_URL = "https://thenewstack.io/python/"
QUERY = "machine learning"


def main():

    print("=" * 70)
    print("Python Archives TF-IDF 權重與相似度檢查")
    print("=" * 70)

    # 載入索引
    index_data = load_index()

    (
        tfidf_data,
        idf_data,
        postings_data,
        document_norms,
        document_info
    ) = index_data

    # 找出目標文件 DocID
    target_doc_id = None

    for doc_id, info in document_info.items():

        if info.get("url", "").rstrip("/") == TARGET_URL.rstrip("/"):
            target_doc_id = doc_id
            break

    if target_doc_id is None:
        print("[錯誤] 找不到目標文件")
        return

    print(f"\nDocID：{target_doc_id}")
    print(f"URL：{document_info[target_doc_id]['url']}")
    print(f"標題：{document_info[target_doc_id]['title']}")

    # --------------------------------------------------
    # 1. 查詢詞前處理
    # --------------------------------------------------

    query_tokens = preprocess_text(QUERY)

    print("\n【1. 查詢詞前處理】")
    print("原始查詢：", QUERY)
    print("查詢詞：", query_tokens)

    # --------------------------------------------------
    # 2. Query TF-IDF
    # --------------------------------------------------

    query_tf = calculate_query_tf(query_tokens)
    query_tfidf = calculate_query_tfidf(
        query_tf,
        idf_data
    )

    query_norm = calculate_query_norm(query_tfidf)

    print("\n【2. 查詢詞 TF-IDF】")

    for term in query_tfidf:

        print(f"\n詞彙：{term}")
        print(f"Query TF：{query_tf[term]:.8f}")
        print(f"IDF：{idf_data[term]:.8f}")
        print(f"Query TF-IDF：{query_tfidf[term]:.8f}")

    print(f"\nQuery Norm：{query_norm:.8f}")

    # --------------------------------------------------
    # 3. 目標文件 TF-IDF
    # --------------------------------------------------

    document_vector = tfidf_data[target_doc_id]

    print("\n【3. 目標文件 TF-IDF】")

    dot_product = 0

    for term in query_tfidf:

        document_weight = document_vector.get(term, 0)

        contribution = (
            query_tfidf[term] * document_weight
        )

        dot_product += contribution

        print(f"\n詞彙：{term}")
        print(f"Document TF-IDF：{document_weight:.8f}")
        print(f"內積貢獻：{contribution:.8f}")

    # --------------------------------------------------
    # 4. Document Norm
    # --------------------------------------------------

    document_norm = document_norms[target_doc_id]

    print("\n【4. 文件向量長度】")
    print(f"Document Norm：{document_norm:.8f}")

    # --------------------------------------------------
    # 5. Cosine Similarity
    # --------------------------------------------------

    denominator = query_norm * document_norm

    score = (
        dot_product / denominator
        if denominator > 0 else 0
    )

    print("\n【5. Cosine Similarity 計算】")
    print(f"內積：{dot_product:.8f}")
    print(f"Query Norm：{query_norm:.8f}")
    print(f"Document Norm：{document_norm:.8f}")
    print(f"分母：{denominator:.8f}")
    print(f"Cosine Similarity：{score:.8f}")

    # --------------------------------------------------
    # 6. 實際搜尋排名
    # --------------------------------------------------

    search_result = search(
        QUERY,
        index_data,
        top_k=len(tfidf_data)
    )

    ranking = None

    for rank, result in enumerate(
        search_result["results"], start=1
    ):

        if result["url"].rstrip("/") == TARGET_URL.rstrip("/"):
            ranking = rank
            break

    print("\n【6. 搜尋排名】")

    if ranking is not None:
        print(f"實際排名：第 {ranking} 名")
    else:
        print("未進入搜尋結果")

    print(f"相似度：{score:.8f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()