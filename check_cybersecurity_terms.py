import json
import re
import os
from collections import defaultdict


# ============================================================
# 1. 設定資料來源
# ============================================================

FILES = [
    "database/pages_Ａ.json",
    "database/pages_B.json"
]

OUTPUT_DIR = "evaluation"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "cybersecurity_term_check.json"
)


# ============================================================
# 2. 設定資安相關名詞
# ============================================================

TERMS = [
    "cybersecurity",
    "cyber security",
    "cyber attack",
    "cyber attacks",
    "cyberattack",
    "cyberattacks",
    "network security",
    "security attack",
    "security breach",
    "data breach",
    "data leak",
    "data theft",
    "hacking",
    "hacker",
    "hackers",
    "intrusion",
    "malware",
    "ransomware",
    "phishing",
    "spyware",
    "trojan",
    "virus",
    "botnet",
    "ddos",
    "denial of service",
    "credential theft",
    "cyber threat",
    "cyber incident"
]


# ============================================================
# 3. 載入文章資料
# ============================================================

def load_documents():

    documents = []

    for filepath in FILES:

        if not os.path.isfile(filepath):
            print(f"[WARNING] 找不到檔案：{filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            documents.extend(data)

        elif isinstance(data, dict):
            if "documents" in data:
                documents.extend(data["documents"])
            else:
                print(f"[WARNING] 無法辨識 JSON 結構：{filepath}")

        print(
            f"[讀取成功] {filepath}："
            f"{len(data) if isinstance(data, list) else len(data.get('documents', []))} 篇"
        )

    return documents


# ============================================================
# 4. 檢查名詞是否存在於文章內文
# ============================================================

def check_terms(documents):

    term_results = defaultdict(list)

    for doc in documents:

        title = doc.get("title", "")
        url = doc.get("url", "")
        content = doc.get("text", "")

        if not isinstance(content, str):
            continue

        text = content.lower()

        for term in TERMS:

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(term.lower())
                + r"(?![a-z0-9])"
            )

            matches = list(re.finditer(pattern, text))

            if matches:

                term_results[term].append({
                    "title": title,
                    "url": url,
                    "occurrences": len(matches)
                })

    return term_results


# ============================================================
# 5. 主程式
# ============================================================

if __name__ == "__main__":

    print("=" * 65)
    print("Cybersecurity 相關名詞資料庫檢查")
    print("=" * 65)

    documents = load_documents()

    print(f"\n總文件數量：{len(documents)}")

    results = check_terms(documents)

    output_data = {
        "topic": "Cybersecurity Attacks",
        "total_documents": len(documents),
        "terms": []
    }

    print("\n" + "=" * 65)
    print("相關名詞出現統計")
    print("=" * 65)

    for term in TERMS:

        matched_docs = results.get(term, [])

        item = {
            "term": term,
            "document_count": len(matched_docs),
            "documents": matched_docs
        }

        output_data["terms"].append(item)

        print(
            f"{term:<25} "
            f"出現在 {len(matched_docs):>3} 篇文章"
        )

    # 找出至少出現一次的名詞
    existing_terms = [
        item for item in output_data["terms"]
        if item["document_count"] > 0
    ]

    output_data["existing_term_count"] = len(existing_terms)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\n" + "=" * 65)
    print("檢查完成")
    print("=" * 65)

    print(f"檢查名詞數量：{len(TERMS)}")
    print(f"有出現在資料庫的名詞：{len(existing_terms)}")
    print(f"JSON 儲存位置：{OUTPUT_FILE}")