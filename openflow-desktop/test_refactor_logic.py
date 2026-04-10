
import unittest
import os
import sys
from unittest.mock import MagicMock

# Mock cv2 and PIL.Image before importing main
sys.modules['cv2'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

from main import MaterialProcessor

class TestRefactorLogic(unittest.TestCase):
    def setUp(self):
        self.processor = MaterialProcessor()
        self.test_dir = "test_media_folder"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)

    def test_scan_folder_empty(self):
        results = self.processor.scan_folder(self.test_dir)
        self.assertEqual(results, [])

    def test_scan_folder_with_file(self):
        # Create a dummy file
        dummy_file = os.path.join(self.test_dir, "test.mp4")
        with open(dummy_file, 'w') as f:
            f.write("dummy")

        # Mock get_media_dimensions to return something known
        self.processor.get_media_dimensions = MagicMock(return_value=(1280, 720))

        results = self.processor.scan_folder(self.test_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file'], "test.mp4")
        self.assertEqual(results[0]['actual_size'], "1280*720")

    def test_validate_folder_logic(self):
        dummy_file = os.path.join(self.test_dir, "test.mp4")
        with open(dummy_file, 'w') as f:
            f.write("dummy")

        self.processor.get_media_dimensions = MagicMock(return_value=(1280, 720))

        required_specs = {"1280*720": 1}
        report = self.processor.validate_folder(self.test_dir, required_specs)

        # Check if the file was validated correctly
        file_report = [item for item in report if item['file'] == "test.mp4"][0]
        self.assertEqual(file_report['status'], "校验通过")

        # Check if total stats are correct
        stats_report = [item for item in report if item['file'] == "[整体统计]"][0]
        self.assertEqual(stats_report['status'], "数量达标")

if __name__ == "__main__":
    unittest.main()
