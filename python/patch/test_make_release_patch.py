"""Tests for make_release_patch.py.

Uses small synthetic files only -- never the real 739 MB BINs.
Run: python3 python/patch/test_make_release_patch.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_release_patch import md5_file, sha256_file, verify_source  # noqa: E402


def make_pair(tmp):
    """Create a small fake original/patched BIN pair (100 KB each)."""
    orig = os.path.join(tmp, "orig.bin")
    patched = os.path.join(tmp, "patched.bin")
    data = bytes(range(256)) * 400  # 102,400 bytes
    with open(orig, "wb") as f:
        f.write(data)
    mod = bytearray(data)
    mod[5000:5010] = b"KOREANTEXT"
    with open(patched, "wb") as f:
        f.write(bytes(mod))
    return orig, patched


def test_md5_and_sha256():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "x.bin")
        with open(p, "wb") as f:
            f.write(b"hello")
        assert md5_file(p) == "5d41402abc4b2a76b9719d911017c592", md5_file(p)
        assert sha256_file(p) == ("2cf24dba5fb0a30e26e83b2ac5b9e29e"
                                  "1b161e5c1fa7425e73043362938b9824"), sha256_file(p)


def test_verify_source_accepts_matching_file():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        # Must return without raising.
        verify_source(orig, md5_file(orig), os.path.getsize(orig))


def test_verify_source_rejects_wrong_size():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        try:
            verify_source(orig, md5_file(orig), os.path.getsize(orig) + 1)
        except SystemExit as e:
            assert "size mismatch" in str(e), e
        else:
            raise AssertionError("expected SystemExit for wrong size")


def test_verify_source_rejects_wrong_md5():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        try:
            verify_source(orig, "0" * 32, os.path.getsize(orig))
        except SystemExit as e:
            assert "MD5 mismatch" in str(e), e
        else:
            raise AssertionError("expected SystemExit for wrong md5")


if __name__ == "__main__":
    test_md5_and_sha256()
    test_verify_source_accepts_matching_file()
    test_verify_source_rejects_wrong_size()
    test_verify_source_rejects_wrong_md5()
    print("PASS: all make_release_patch tests")
