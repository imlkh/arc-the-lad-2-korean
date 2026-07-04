"""Tests for make_release_patch.py.

Uses small synthetic files only -- never the real 739 MB BINs.
Run: python3 python/patch/test_make_release_patch.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_release_patch import (  # noqa: E402
    md5_file, sha256_file, verify_source,
    check_xdelta3, build_patch, verify_patch, main)


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


def test_check_xdelta3_found():
    path = check_xdelta3()
    assert os.path.basename(path) == "xdelta3", path


def test_build_and_verify_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        patch = os.path.join(tmp, "test.xdelta")
        build_patch(orig, patched, patch)
        assert os.path.getsize(patch) > 0
        # Must not raise, and must keep the patch file.
        verify_patch(orig, patch, md5_file(patched))
        assert os.path.exists(patch)


def test_verify_patch_rejects_wrong_md5_and_deletes_patch():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        patch = os.path.join(tmp, "test.xdelta")
        build_patch(orig, patched, patch)
        try:
            verify_patch(orig, patch, "0" * 32)
        except SystemExit as e:
            assert "round-trip" in str(e), e
            assert not os.path.exists(patch), "bad patch must be deleted"
        else:
            raise AssertionError("expected SystemExit for wrong md5")
        # No temp .bin files may be left behind.
        leftovers = [f for f in os.listdir(tmp)
                     if f.endswith(".bin") and f not in ("orig.bin", "patched.bin")]
        assert leftovers == [], leftovers


def test_main_builds_release_package():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        cue = os.path.join(tmp, "test.cue")
        with open(cue, "w") as f:
            f.write('FILE "Arc the Lad II (Korean Patch).bin" BINARY\n'
                    '  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
        out = os.path.join(tmp, "release")
        main(["--original", orig, "--patched", patched, "--cue", cue,
              "--out", out,
              "--expected-md5", md5_file(orig),
              "--expected-size", str(os.path.getsize(orig))])
        [vdir] = os.listdir(out)  # one version directory
        vpath = os.path.join(out, vdir)
        files = sorted(os.listdir(vpath))
        patch_names = [f for f in files if f.endswith(".xdelta")]
        assert len(patch_names) == 1, files
        assert patch_names[0].startswith("arc-the-lad-2-korean-"), patch_names
        assert "Arc the Lad II (Korean Patch).cue" in files, files
        assert "README.txt" in files, files
        assert "SHA256SUMS.txt" in files, files
        readme = open(os.path.join(vpath, "README.txt"), encoding="utf-8").read()
        assert "012B023097777CB6CE6A5DE5E0457022" in readme
        assert "Rev 1" in readme
        assert patch_names[0] in readme
        sums = open(os.path.join(vpath, "SHA256SUMS.txt")).read().splitlines()
        assert len(sums) == 2, sums  # patch + cue
        for line in sums:
            digest, name = line.split("  ", 1)
            assert digest == sha256_file(os.path.join(vpath, name)), line


def test_main_rerun_removes_stale_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        cue = os.path.join(tmp, "test.cue")
        with open(cue, "w") as f:
            f.write('FILE "Arc the Lad II (Korean Patch).bin" BINARY\n')
        out = os.path.join(tmp, "release")
        argv = ["--original", orig, "--patched", patched, "--cue", cue,
                "--out", out,
                "--expected-md5", md5_file(orig),
                "--expected-size", str(os.path.getsize(orig))]
        main(argv)
        [vdir] = os.listdir(out)
        vpath = os.path.join(out, vdir)
        # Plant a stale artifact from a hypothetical earlier build.
        with open(os.path.join(vpath, "stale-old-version.xdelta"), "w") as f:
            f.write("stale")
        main(argv)
        files = sorted(os.listdir(vpath))
        assert "stale-old-version.xdelta" not in files, files
        assert len(files) == 4, files  # xdelta, cue, README, SHA256SUMS


def test_main_rejects_missing_cue():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        missing_cue = os.path.join(tmp, "nope.cue")
        try:
            main(["--original", orig, "--patched", patched,
                  "--cue", missing_cue,
                  "--out", os.path.join(tmp, "release"),
                  "--expected-md5", md5_file(orig),
                  "--expected-size", str(os.path.getsize(orig))])
        except SystemExit as e:
            assert "--cue file not found" in str(e), e
        else:
            raise AssertionError("expected SystemExit for missing cue")


if __name__ == "__main__":
    test_md5_and_sha256()
    test_verify_source_accepts_matching_file()
    test_verify_source_rejects_wrong_size()
    test_verify_source_rejects_wrong_md5()
    test_check_xdelta3_found()
    test_build_and_verify_roundtrip()
    test_verify_patch_rejects_wrong_md5_and_deletes_patch()
    test_main_builds_release_package()
    test_main_rerun_removes_stale_artifacts()
    test_main_rejects_missing_cue()
    print("PASS: all make_release_patch tests")
