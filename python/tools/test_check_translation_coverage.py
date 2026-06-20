import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_translation_coverage as cov


class TestContainsJapanese(unittest.TestCase):
    def test_hiragana_detected(self):
        self.assertTrue(cov.contains_japanese("おはよう"))

    def test_katakana_detected(self):
        self.assertTrue(cov.contains_japanese("ベンチ"))

    def test_korean_only_not_detected(self):
        self.assertFalse(cov.contains_japanese("안녕하세요"))

    def test_middle_dot_not_detected(self):
        # ・ (U+30FB) is intentional punctuation, not untranslated kana
        self.assertFalse(cov.contains_japanese("그렇군・・・"))

    def test_jp_punctuation_not_detected(self):
        self.assertFalse(cov.contains_japanese("「안녕」、반가워。…"))

    def test_mixed_flags_true(self):
        self.assertTrue(cov.contains_japanese("베조아、みつかった"))


if __name__ == "__main__":
    unittest.main()
