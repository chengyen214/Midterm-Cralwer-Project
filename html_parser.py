from datetime import datetime
from html_parser import parse_html

# 以下變數由 crawler 的下載流程取得
html = response.text
url = response.url

# 記錄下載時間
fetch_time = datetime.now().astimezone().isoformat()

# 呼叫 HTML 解析器
parsed = parse_html(html)

if parsed is not None:
    page_data = {
        "url": url,
        "title": parsed["title"],
        "text": parsed["text"],
        "fetch_time": fetch_time
    }

    print(page_data)