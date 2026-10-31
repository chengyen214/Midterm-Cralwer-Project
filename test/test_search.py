import sys
import unittest
from pathlib import Path

# 將專案根目錄加入 Python 搜尋路徑
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from search import (
    load_index,
    search,
    calculate_cosine_similarity
)


class TestSearchEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 所有測試共用同一份索引
        cls.index_data = load_index()

    def test_normal_search(self):
        """測試正常關鍵字搜尋"""

        response = search(
            "cloud storage",
            self.index_data
        )

        self.assertIsInstance(response, dict)
        self.assertGreater(
            response["total_indexed_pages"], 0
        )

        print("\n[Test 1] Normal Search: PASS")

    def test_multiple_keywords(self):
        """測試多個關鍵字搜尋"""

        response = search(
            "artificial intelligence machine learning",
            self.index_data
        )

        self.assertIsInstance(response["results"], list)

        print("[Test 2] Multiple Keywords: PASS")

    def test_unknown_keyword(self):
        """測試完全不存在於索引中的關鍵字"""

        from preprocessor import preprocess_text

        unknown_query = "xyzqwerty987654"

        query_tokens = preprocess_text(unknown_query)

        idf_data = self.index_data[1]

        # 確認所有查詢詞都不在索引中
        for token in query_tokens:
            self.assertNotIn(
                token,
                idf_data,
                f"測試詞彙 {token} 意外存在於索引中"
            )

        response = search(
            unknown_query,
            self.index_data
        )

        self.assertEqual(response["total_results"], 0)
        self.assertEqual(response["results"], [])

        print("[Test 3] Unknown Keyword: PASS")

    def test_top_10(self):
        """測試最多回傳 10 筆結果"""

        response = search(
            "technology",
            self.index_data,
            top_k=10
        )

        self.assertLessEqual(
            len(response["results"]),
            10
        )

        print("[Test 5] Top 10: PASS")

    def test_result_fields(self):
        """測試前端所需欄位是否完整"""

        response = search(
            "cloud storage",
            self.index_data
        )

        required_fields = {
            "title",
            "url",
            "snippet",
            "score"
        }

        for result in response["results"]:

            self.assertTrue(
                required_fields.issubset(result.keys())
            )

            self.assertIsInstance(result["title"], str)
            self.assertIsInstance(result["url"], str)
            self.assertIsInstance(result["snippet"], str)
            self.assertIsInstance(result["score"], (int, float))

        print("[Test 6] Result Fields: PASS")

    def test_cosine_similarity(self):
        """測試 Cosine Similarity 數學計算"""

        query_tfidf = {
            "cloud": 1.0,
            "storage": 1.0
        }

        document_tfidf = {
            "cloud": 1.0,
            "storage": 1.0
        }

        query_norm = 2 ** 0.5
        document_norm = 2 ** 0.5

        score = calculate_cosine_similarity(
            query_tfidf,
            document_tfidf,
            query_norm,
            document_norm
        )

        self.assertAlmostEqual(score, 1.0, places=6)

        print("[Test 7] Cosine Similarity: PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)