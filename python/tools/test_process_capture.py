import unittest, tempfile, os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_capture as pc

# Treasure-chest bytes (known real missed Japanese line "おれはたからばこだ")
CHEST = "05 2A 1A 10 06 27 3E 0A 39"

class TestParseAndClassify(unittest.TestCase):
    def _log(self, text):
        fd, p = tempfile.mkstemp(suffix=".log"); os.close(fd)
        Path(p).write_text(text, encoding="utf-8"); return Path(p)

    def test_parse_capture_log(self):
        p = self._log(f"addr=0x801A0000 bytes={CHEST}\n"
                      f"# comment line ignored\n"
                      f"addr=0x801A0040 bytes=51 52 63\n")
        out = pc.parse_capture_log(p)
        self.assertEqual(out[0][0], 0x801A0000)
        self.assertEqual(out[0][1], bytes([0x05,0x2A,0x1A,0x10,0x06,0x27,0x3E,0x0A,0x39]))
        self.assertEqual(len(out), 2)

    def test_decode_line_readable(self):
        table = pc.dt.build_decode_table()
        text = pc.decode_line(bytes([0x05,0x2A,0x1A,0x10,0x06,0x27,0x3E,0x0A,0x39]), table)
        self.assertIn("たからばこ", text)

    def test_contains_japanese_on_text(self):
        # utility operates on decoded TEXT, not raw bytes
        self.assertTrue(pc.contains_japanese("おはよう"))
        self.assertFalse(pc.contains_japanese("안녕하세요"))


class TestMapAndEmit(unittest.TestCase):
    def setUp(self):
        if not (pc.GAME_DIR / "S700.STG").exists():
            self.skipTest("original STG binaries not present")

    def test_find_offsets_treasure_chest(self):
        raw = bytes([0x05,0x2A,0x1A,0x10,0x06,0x27,0x3E,0x0A,0x39])
        hits = pc.find_offsets(raw)
        self.assertTrue(any(stage and isinstance(off, int) for stage, off in hits),
                        "treasure-chest bytes should be found in at least one STG")

    def test_process_flags_missed_by_original_match(self):
        # chest bytes match an original STG -> missed, with offset + readable JP
        fd, p = tempfile.mkstemp(suffix=".log"); os.close(fd)
        Path(p).write_text(
            "addr=0x801A0000 bytes=05 2A 1A 10 06 27 3E 0A 39\n"
            # bytes that do NOT appear in any original STG -> NOT missed (e.g. a
            # translated/Korean line); use an implausible run.
            "addr=0x801A0050 bytes=EE EE EE EE EE EE EE EE EE EE\n",
            encoding="utf-8")
        result = pc.process(Path(p))
        self.assertEqual(len(result["missed"]), 1)   # only the chest matched
        m = result["missed"][0]
        self.assertIn("たからばこ", m["text"])
        self.assertIsNotNone(m["stage"])
        os.unlink(p)

if __name__ == "__main__":
    unittest.main()
