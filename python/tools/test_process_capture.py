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

if __name__ == "__main__":
    unittest.main()
