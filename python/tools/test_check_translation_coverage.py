import unittest
from pathlib import Path
import sys
import tempfile
import os

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


class TestParsers(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        Path(path).write_text(text, encoding="utf-8")
        return Path(path)

    def test_parse_translation_file(self):
        p = self._write(
            "# header\n"
            "  0x003ABB32 [0x8005] [script:BB 36]기간한정\n"
            "  --- context ---\n"
            "  0x003ABC02 [0x8005] [script:A9 00]베조아\n"
        )
        out = cov.parse_translation_file(p)
        self.assertEqual(out[0x003ABB32], "기간한정")
        self.assertEqual(out[0x003ABC02], "베조아")
        self.assertEqual(len(out), 2)

    def test_parse_decoded_offsets(self):
        p = self._write(
            "  0x000B4000 [0xFFFE] [script:01 02]text\n"
            "  0x000B4050 [0x8005] [script:03 04]more\n"
        )
        self.assertEqual(cov.parse_decoded_offsets(p), {0x000B4000, 0x000B4050})


if __name__ == "__main__":
    unittest.main()
