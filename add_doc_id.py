
import json
from pathlib import Path

from preprocessor import get_preprocessed_documents

# 原始檔案
INPUT_FILE = Path("database/pages_Ａ.json")

# 新檔案，不覆蓋原始資料
OUTPUT_FILE = Path("database/pages_Ａ_with_doc_id.json")


def main():
    # 取得前處理後的文件及 DocID
    documents = get_preprocessed_documents()

    # 建立 URL 與 DocID 的對應表
    url_to_doc_id = {
        doc["url"]: doc["doc_id"]
        for doc in documents
        if doc.get("url")
    }

    # 建立 DocID 與 URL 的反向對應表
    doc_id_to_url = {
        doc["doc_id"]: doc["url"]
        for doc in documents
    }

    # 讀取原始 JSON
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        articles = json.load(file)

    matched = 0
    unmatched = 0
    unmatched_articles = []
    used_doc_ids = set()
    duplicate_doc_ids = []

    # 新增 DocID
    for article in articles:
        url = article.get("url")
        doc_id = url_to_doc_id.get(url)

        if doc_id:
            article["doc_id"] = doc_id
            matched += 1

            # 檢查是否有重複 DocID
            if doc_id in used_doc_ids:
                duplicate_doc_ids.append(doc_id)
            else:
                used_doc_ids.add(doc_id)

        else:
            article["doc_id"] = None
            unmatched += 1

            unmatched_articles.append({
                "url": url,
                "title": article.get("title"),
                "reason": (
                    "缺少 URL" if not url
                    else "URL 無法在前處理文件中找到對應"
                )
            })

    # DocID 對應驗證
    correct = 0
    incorrect = 0
    validation_errors = []

    for article in articles:
        doc_id = article.get("doc_id")

        if doc_id is None:
            continue

        expected_url = doc_id_to_url.get(doc_id)
        actual_url = article.get("url")

        if expected_url == actual_url:
            correct += 1
        else:
            incorrect += 1
            validation_errors.append({
                "doc_id": doc_id,
                "actual_url": actual_url,
                "expected_url": expected_url
            })

    # 輸出新 JSON，不覆蓋原始檔案
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            articles,
            file,
            ensure_ascii=False,
            indent=4
        )

    # 顯示統計結果
    print("=" * 60)
    print("DocID 對應結果")
    print("=" * 60)

    print(f"原始文章數量：{len(articles)}")
    print(f"前處理文件數量：{len(documents)}")
    print(f"成功對應：{matched}")
    print(f"未成功對應：{unmatched}")

    # 顯示未成功對應文章
    if unmatched_articles:
        print("\n[未成功對應的文章]")
        print("-" * 60)

        for index, article in enumerate(unmatched_articles, start=1):
            print(f"\n第 {index} 篇")
            print(f"標題：{article['title']}")
            print(f"URL：{article['url']}")
            print(f"原因：{article['reason']}")

    # 顯示驗證結果
    print("\n[DocID 對應驗證]")
    print("-" * 60)
    print(f"驗證成功：{correct}")
    print(f"驗證失敗：{incorrect}")

    if validation_errors:
        print("\n[對應錯誤]")
        for error in validation_errors:
            print(f"DocID：{error['doc_id']}")
            print(f"目前 URL：{error['actual_url']}")
            print(f"預期 URL：{error['expected_url']}")

    # 顯示重複 DocID
    if duplicate_doc_ids:
        print("\n[重複 DocID]")
        for doc_id in duplicate_doc_ids:
            print(doc_id)
    else:
        print("\n沒有發現重複 DocID。")

    # 最終結果
    print("\n" + "=" * 60)
    if incorrect == 0 and not duplicate_doc_ids:
        print("[PASS] DocID 對應驗證通過")
    else:
        print("[WARNING] 請檢查 DocID 對應錯誤")

    print(f"新檔案位置：{OUTPUT_FILE}")
    print("原始 pages_Ａ.json 未被修改。")
    print("=" * 60)


if __name__ == "__main__":
    main()
