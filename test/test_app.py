import sys
import unittest
from pathlib import Path

# 加入專案根目錄
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app


class TestFlaskApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 建立 Flask 測試用戶端
        cls.client = app.test_client()

    # --------------------------------------------------------
    # Test 1：首頁是否正常開啟
    # --------------------------------------------------------

    def test_homepage(self):

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

        print("\n[Test 1] Homepage: PASS")

    # --------------------------------------------------------
    # Test 2：是否顯示總索引頁數
    # --------------------------------------------------------

    def test_total_indexed_pages(self):

        response = self.client.get("/")

        html = response.get_data(as_text=True)

        self.assertIn("Total Indexed Pages", html)

        print("[Test 2] Total Indexed Pages: PASS")

    # --------------------------------------------------------
    # Test 3：搜尋框是否存在
    # --------------------------------------------------------

    def test_search_box(self):

        response = self.client.get("/")

        html = response.get_data(as_text=True)

        self.assertIn('name="q"', html)
        self.assertIn("Search", html)

        print("[Test 3] Search Box: PASS")

    # --------------------------------------------------------
    # Test 4：正常搜尋
    # --------------------------------------------------------

    def test_normal_search(self):

        response = self.client.get(
            "/?q=cloud+storage"
        )

        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)

        self.assertIn("Search Results", html)

        print("[Test 4] Normal Search: PASS")

    # --------------------------------------------------------
    # Test 5：搜尋結果欄位
    # --------------------------------------------------------

    def test_result_fields(self):

        response = self.client.get(
            "/?q=cloud+storage"
        )

        html = response.get_data(as_text=True)

        self.assertIn("Similarity Score", html)

        print("[Test 5] Result Fields: PASS")

    # --------------------------------------------------------
    # Test 6：空白查詢
    # --------------------------------------------------------

    def test_empty_query(self):

        response = self.client.get(
            "/?q="
        )

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "Please enter a search query.",
            html
        )

        print("[Test 6] Empty Query: PASS")

    # --------------------------------------------------------
    # Test 7：未知關鍵字
    # --------------------------------------------------------

    def test_unknown_keyword(self):

        response = self.client.get(
            "/?q=xyzqwerty987654"
        )

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "No results found.",
            html
        )

        print("[Test 7] Unknown Keyword: PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)