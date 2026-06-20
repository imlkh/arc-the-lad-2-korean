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


class TestLoadInvalidOffsets(unittest.TestCase):
    def setUp(self):
        self._orig = cov.DECODED_DIR
        self._tmp = Path(tempfile.mkdtemp())
        cov.DECODED_DIR = self._tmp

    def tearDown(self):
        cov.DECODED_DIR = self._orig

    def test_parses_line_prefixed_offsets(self):
        (self._tmp / "S200_STG_invalid_report.txt").write_text(
            "# header\n"
            "## Category 1\n"
            "  Line 1449: 0x003ABC02 [0x8005] [script:A9 00]ガベージ\n"
            "\n"
            "  Line 1450: 0x003ABC0F [0x8005] debug\n",
            encoding="utf-8")
        self.assertEqual(cov.load_invalid_offsets("S200"),
                         {0x003ABC02, 0x003ABC0F})

    def test_missing_report_returns_empty(self):
        self.assertEqual(cov.load_invalid_offsets("ZZ99"), set())


class TestTier1(unittest.TestCase):
    def test_flags_only_kana_entries(self):
        translations = {
            0x10: "안녕하세요",        # translated
            0x20: "おはよう",          # untranslated hiragana
            0x30: "그렇군・・・",       # translated, middle dot OK
            0x40: "ベンチ",            # untranslated katakana
        }
        out = cov.tier1_untranslated(translations)
        self.assertEqual(out, [(0x20, "おはよう"), (0x40, "ベンチ")])


if __name__ == "__main__":
    unittest.main()
