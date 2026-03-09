
import unittest
import json
import sys
import os

# 将当前目录添加到路径以便导入 main_window
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from openflow_desktop.main_window import preprocess_json_text
except ImportError:
    # 兼容直接在当前目录运行
    from main_window import preprocess_json_text

class TestJsonParsing(unittest.TestCase):
    def test_bom_removal(self):
        raw = '\ufeff{"key": "value"}'
        clean = preprocess_json_text(raw)
        self.assertEqual(clean, '{"key": "value"}')
        self.assertEqual(json.loads(clean), {"key": "value"})

    def test_comment_removal_with_url(self):
        raw = """
        {
            "url": "https://example.com", // 这是一个 URL
            "desc": "测试注释" // 这是一个注释
        }
        """
        clean = preprocess_json_text(raw)
        # 确保 https:// 还在
        self.assertIn("https://example.com", clean)
        # 排除注释内容 (简单校验)
        self.assertNotIn("这是一个 URL", clean)
        
        # 验证解析
        data = json.loads(clean, strict=False)
        self.assertEqual(data["url"], "https://example.com")
        self.assertEqual(data["desc"], "测试注释")

    def test_control_character_handling(self):
        # 包含物理控制字符的 JSON 是不合法的，但 strict=False 允许解析
        raw = '{"key": "value\x01\x1f"}'
        clean = preprocess_json_text(raw)
        # 验证 strict=False 能解
        data = json.loads(clean, strict=False)
        self.assertEqual(data["key"], "value\x01\x1f")

if __name__ == '__main__':
    unittest.main()
