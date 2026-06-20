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


class TestTier2(unittest.TestCase):
    def setUp(self):
        self._real_scan = cov.dt.scan_stg

    def tearDown(self):
        cov.dt.scan_stg = self._real_scan

    def test_captures_rejected_japanese_only(self):
        # kept set: offset 0x10 ; full set: 0x10 + rejects 0x20(jp), 0x30(garbage ascii), 0x40(jp but invalid), 0x50(jp but already decoded)
        def fake_scan(data, table, use_heuristics=True, filter_garbage=True):
            kept = [(0x10, 4, "안녕", 0xFFFE)]
            full = kept + [
                (0x20, 6, "みつかった", 0x8005),   # real reject -> expect captured
                (0x30, 3, "Xab", 0x8005),          # not japanese -> excluded
                (0x40, 5, "ほげ", 0x8005),          # japanese but invalid offset
                (0x50, 5, "ふが", 0x8005),          # japanese but already decoded
            ]
            return (kept if filter_garbage else full), [], {}
        cov.dt.scan_stg = fake_scan

        out = cov.tier2_decoder_rejects(
            data=b"", decode_table={},
            decoded_offsets={0x50}, invalid_offsets={0x40},
        )
        self.assertEqual(out, [(0x20, "みつかった")])


class TestByteAccountability(unittest.TestCase):
    def test_unaccounted_japanese_run_detected(self):
        table = cov.dt.build_decode_table()
        # Pick three kana chars that round-trip through the table.
        inv = {v: k for k, v in table.items() if isinstance(k, int) and 1 <= k <= 0xEE}
        kana = [c for c in ("お", "は", "よ", "う", "み", "つ") if c in inv][:3]
        self.assertGreaterEqual(len(kana), 3, "need 3 single-byte kana in table")
        payload = bytes(inv[c] for c in kana) + b"\x00"

        chunk = cov.dt.STG_CHUNK_SIZE
        text_off = cov.dt.STG_TEXT_REGION_OFFSET
        data = bytearray(chunk)
        data[text_off:text_off + len(payload)] = payload

        frac, cands = cov.byte_accountability(
            bytes(data), table, decoded_offsets=set(), invalid_offsets=set())
        offs = [c[0] for c in cands]
        self.assertIn(text_off, offs)
        self.assertLess(frac, 1.0)

    def test_decoded_run_is_accounted(self):
        table = cov.dt.build_decode_table()
        inv = {v: k for k, v in table.items() if isinstance(k, int) and 1 <= k <= 0xEE}
        kana = [c for c in ("お", "は", "よ", "う", "み", "つ") if c in inv][:3]
        payload = bytes(inv[c] for c in kana) + b"\x00"
        chunk = cov.dt.STG_CHUNK_SIZE
        text_off = cov.dt.STG_TEXT_REGION_OFFSET
        data = bytearray(chunk)
        data[text_off:text_off + len(payload)] = payload
        # Mark that offset as already decoded -> must NOT be a Tier-3 candidate.
        _frac, cands = cov.byte_accountability(
            bytes(data), table, decoded_offsets={text_off}, invalid_offsets=set())
        self.assertNotIn(text_off, [c[0] for c in cands])


if __name__ == "__main__":
    unittest.main()
