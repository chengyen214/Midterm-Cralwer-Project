
from flask import Flask, render_template, request

from search import load_index, search
from bm25 import build_bm25_index, bm25_search

app = Flask(__name__)

print("[載入索引中] 請稍候...")

index_data = load_index()

total_documents = len(index_data[0])

# BM25 index
print("[建立 BM25 索引中] 請稍候...")

bm25_index = build_bm25_index()

# Reuse document metadata and original text from search.py
document_info = index_data[4]

print("[載入完成]")
print(f"總索引頁數：{total_documents}")


@app.route("/")
def index():

    query = request.args.get("q", "").strip()

    method = request.args.get(
        "method",
        "tfidf"
    )

    if method not in ("tfidf", "bm25"):
        method = "tfidf"

    if "q" not in request.args:

        return render_template(
            "index.html",
            query="",
            method=method,
            searched=False,
            total_documents=total_documents,
            results=[]
        )

    if method == "bm25":

        output = bm25_search(
            query,
            document_info,
            bm25_index,
            top_k=10
        )

    else:

        output = search(
            query,
            index_data,
            top_k=10
        )

    return render_template(
        "index.html",
        query=query,
        method=method,
        searched=True,
        is_empty_query=(query == ""),
        results=output["results"],
        total_documents=total_documents,
        total_results=output["total_results"]
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
