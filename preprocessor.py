
import json
import re
import html
from pathlib import Path
from bs4 import BeautifulSoup


# ============================================================
# 1. 路徑設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"

INPUT_FILES = [
    DATABASE_DIR / "pages_Ａ.json",
    DATABASE_DIR / "pages_B.json",
]


# ============================================================
# 2. 停用詞
# ============================================================

STOP_WORDS = {
    "a", "an", "the",
    "and", "or", "but",
    "is", "am", "are", "was", "were",
    "be", "been", "being",
    "of", "in", "on", "at", "to",
    "for", "from", "by", "with",
    "as", "into", "about", "between",
    "this", "that", "these", "those",
    "it", "its", "they", "them",
    "their", "he", "she", "we", "you",
    "i", "my", "our", "your",
    "have", "has", "had",
    "do", "does", "did",
    "can", "could", "will", "would",
    "should", "may", "might",
    "not", "no", "nor",
    "if", "then", "than",
    "when", "where", "which",
    "who", "what", "how",
    "also", "just", "more", "most",
    "some", "any", "all",
    "such", "other", "only",
    "very", "up", "out", "over",
    "after", "before", "during",
    "while", "through", "because",
    "however", "therefore",
}


# ============================================================
# 3. HTML 清理
# ============================================================

def clean_html(text):
    """
    清除 HTML 標籤、Script、Style 等非正文內容。
    同時處理 HTML entities 和多餘空白。
    """

    if not isinstance(text, str):
        return ""

    soup = BeautifulSoup(text, "html.parser")

    for tag in soup([
        "script",
        "style",
        "noscript",
        "header",
        "footer",
        "nav"
    ]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = html.unescape(text)

    # 合併多餘空白
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# 4. Tokenization
# ============================================================

def tokenize(text):
    """
    將英文文字轉換成 Token。

    保留特殊技術詞彙：
    C++、C#、Node.js、GPT-4

    一般連字號詞彙會拆開：
    machine-learning -> machine, learning
    """

    text = text.lower()

    pattern = (
        r"c\+\+"
        r"|c#"
        r"|node\.js"
        r"|gpt-\d+(?:\.\d+)*"
        r"|[a-z]+(?:\d+(?:\.\d+)*)?"
    )

    tokens = re.findall(pattern, text)

    return tokens


# ============================================================
# 5. 移除停用詞
# ============================================================

def remove_stop_words(tokens):
    """
    移除英文停用詞。
    """

    return [
        token
        for token in tokens
        if token not in STOP_WORDS
    ]


# ============================================================
# 6. 文字前處理入口
# ============================================================

def preprocess_text(text):
    """
    文字前處理：
    HTML Cleaning -> Lowercase -> Tokenization
    """

    cleaned_text = clean_html(text)

    tokens = tokenize(cleaned_text)

    return tokens


# ============================================================
# 7. 讀取原始 JSON 文件
# ============================================================

def load_documents():
    """
    讀取 pages_Ａ.json 和 pages_B.json。
    """

    documents = []

    for file_path in INPUT_FILES:

        if not file_path.exists():
            print(f"[警告] 找不到檔案：{file_path}")
            continue

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8-sig"
            ) as file:

                data = json.load(file)

            if not isinstance(data, list):
                print(f"[警告] JSON 格式不是 List：{file_path}")
                continue

            documents.extend(data)

            print(
                f"[讀取成功] {file_path.name}："
                f"{len(data)} 篇文件"
            )

        except json.JSONDecodeError as error:
            print(f"[錯誤] JSON 格式錯誤：{file_path}")
            print(error)

        except Exception as error:
            print(f"[錯誤] 讀取失敗：{file_path}")
            print(error)

    return documents


# ============================================================
# 8. 處理所有文件
# ============================================================

def process_documents(documents):
    """
    只對 text 進行文字前處理。
    URL、Title、Fetch Time 保留原始資料。
    """

    processed_documents = []
    seen_urls = set()

    for document in documents:

        url = document.get("url", "")
        title = document.get("title", "")
        text = document.get("text", "")

        # 檢查必要欄位
        if not url or not text:
            continue

        # 避免重複 URL
        if url in seen_urls:
            continue

        seen_urls.add(url)

        # 只對 text 進行前處理
        tokens = preprocess_text(text)

        # 排除沒有有效 Token 的文件
        if not tokens:
            continue

        doc_id = f"D{len(processed_documents) + 1:06d}"

        processed_document = {
            "doc_id": doc_id,
            "url": url,
            "title": title,
            "fetch_time": document.get("fetch_time", ""),
            "tokens": tokens,
            "token_count": len(tokens)
        }

        processed_documents.append(processed_document)

    return processed_documents


# ============================================================
# 9. 提供其他程式呼叫的入口
# ============================================================

def get_preprocessed_documents():
    """
    提供 TF、DF、Indexer 等程式呼叫。

    回傳：
        list：所有前處理後的文件資料
    """

    documents = load_documents()

    processed_documents = process_documents(documents)

    return processed_documents


# ============================================================
# 10. 單獨測試
# ============================================================

if __name__ == "__main__":

    documents = get_preprocessed_documents()

    print("\n" + "=" * 60)
    print("文字前處理結果")
    print("=" * 60)

    print(f"有效文件數量：{len(documents)}")

    if documents:

        first_document = documents[0]

        print("\n第一篇文件資訊")
        print(f"DocID：{first_document['doc_id']}")
        print(f"Title：{first_document['title']}")
        print(f"Token 數量：{first_document['token_count']}")

        print("\nTitle Tokens：")
        print(first_document["title_tokens"][:20])

        print("\nBody Tokens：")
        print(first_document["body_tokens"][:20])

        print("\nCombined Tokens：")
        print(first_document["tokens"][:20])
