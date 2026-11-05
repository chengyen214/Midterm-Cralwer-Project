import json
from pathlib import Path

files = [
    Path("database/pages_Ａ.json"),
    Path("database/pages_B.json")
]

total = 0

for file_path in files:

    with open(file_path, "r", encoding="utf-8") as file:
        articles = json.load(file)

    count = len(articles)
    total += count

    print(f"{file_path}: {count} 篇")

print("-" * 40)
print(f"文章總數：{total} 篇")