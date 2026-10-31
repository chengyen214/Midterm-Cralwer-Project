
from flask import Flask, render_template, request

from search_engine import SearchEngine


# ============================================================
# 1. 建立 Flask 與搜尋引擎（索引只在啟動時載入一次）
# ============================================================

app = Flask(__name__)

print("[載入索引中] 請稍候…")
engine = SearchEngine()
print(f"[載入完成] 總索引頁數：{engine.total_documents}")


# ============================================================
# 2. 搜尋頁面
# ============================================================

@app.route("/")
def index():

    query = request.args.get("q", "").strip()

    # 第一次進入頁面（還沒搜尋）
    if "q" not in request.args:
        return render_template(
            "index.html",
            query="",
            searched=False,
            total_documents=engine.total_documents,
        )

    output = engine.search(query)

    return render_template(
        "index.html",
        query=query,
        searched=True,
        is_empty_query=(query == ""),
        query_terms=output["query_terms"],
        oov_terms=output["oov_terms"],
        results=output["results"],
        total_documents=engine.total_documents,
    )


# ============================================================
# 3. 主程式（本機端演示）
# ============================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
