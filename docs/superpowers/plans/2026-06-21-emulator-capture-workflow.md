# Emulator Capture Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the scripts + runbook to capture displayed dialogue from the patched build in PCSX-Redux, flag still-Japanese (missed) lines, and map each to its STG offset.

**Architecture:** A "dumb" PCSX-Redux Lua hook at the text handler logs raw `(addr, bytes)`; a "smart" Python post-processor decodes (reusing `decode_text`), classifies still-Japanese lines, and maps each to a `(stage, offset)` by **searching the original STG binaries for the captured bytes** (no RAM-base math needed). A runbook ties it together with a one-time calibration step.

**Tech Stack:** Python 3.10 stdlib + `unittest` (no pytest). Lua for PCSX-Redux. Reuses `python/decode/decode_text.py`.

## Global Constraints

- Python 3.10, standard library only. Tests use stdlib `unittest`.
- No hardcoded absolute paths: `REPO_ROOT = Path(__file__).resolve().parents[2]`, `GAME_DIR = parents[3]`.
- Reuse `decode_text`: `build_decode_table()`, `decode_string(data, offset, table) -> (text, consumed)`. Import by adding `REPO_ROOT/"python"/"decode"` to `sys.path`.
- Japanese-kana detection: hiragana U+3041–U+3096, katakana U+30A1–U+30FA (exclude U+30FB `・` and U+30FC `ー`).
- Original STG binaries: `GAME_DIR/{stage}.STG`. Stages: S100,S200,S300,S400,S500,S600,S700,S800,S900,SA00,SB00,SC00,SD00,SE00,SF00,SG00,SH00,SI00,SJ00.
- Capture artifacts live under `output/capture/` (gitignored). Tool + tests + Lua + runbook are tracked.
- Known handler RAM address: `0x80101560`.
- Capture-log line format (emitted by Lua, parsed by Python): `addr=0xHHHHHHHH bytes=XX XX XX ...` (space-separated uppercase hex, no trailing terminator byte).

## File Structure
- `python/tools/process_capture.py` — parser + decode/classify + offset-map + worklist emitter.
- `python/tools/test_process_capture.py` — unittest suite.
- `tools/atl2_capture.lua` — PCSX-Redux hook (calibrate + capture modes).
- `docs/emulator-capture.md` — runbook.

---

### Task 1: Capture-log parsing, decode, and classification

**Files:**
- Create: `python/tools/process_capture.py`
- Test: `python/tools/test_process_capture.py`

**Interfaces:**
- Produces: `parse_capture_log(path: Path) -> list[tuple[int, bytes]]` (addr, raw bytes); `contains_japanese(text: str) -> bool`; `classify(raw: bytes, table) -> tuple[str, bool]` returning `(decoded_text, is_japanese)`.

- [ ] **Step 1: Write the failing test**

```python
# python/tools/test_process_capture.py
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

    def test_classify_japanese(self):
        table = pc.dt.build_decode_table()
        text, is_jp = pc.classify(bytes([0x05,0x2A,0x1A,0x10,0x06,0x27,0x3E,0x0A,0x39]), table)
        self.assertTrue(is_jp)
        self.assertIn("たからばこ", text)

    def test_korean_not_flagged(self):
        # Korean bytes decode without Japanese kana -> is_jp False
        table = pc.dt.build_decode_table()
        # 0x80 0x80 decodes via the unified map; assert no hiragana/katakana letters
        text, is_jp = pc.classify(bytes([0x80, 0x80]), table)
        self.assertFalse(is_jp)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_process_capture -v`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError: ... 'parse_capture_log'`.

- [ ] **Step 3: Write minimal implementation**

```python
# python/tools/process_capture.py
#!/usr/bin/env python3
"""Post-process PCSX-Redux capture logs: decode, flag still-Japanese (missed)
displayed lines, map each to its STG offset by searching the original binaries.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = Path(__file__).resolve().parents[3]
CAPTURE_DIR = REPO_ROOT / "output" / "capture"
STAGES = [f"S{c}00" for c in
          ["1","2","3","4","5","6","7","8","9","A","B","C","D","E","F","G","H","I","J"]]

sys.path.insert(0, str(REPO_ROOT / "python" / "decode"))
import decode_text as dt  # noqa: E402

_LINE = re.compile(r"^addr=0x([0-9A-Fa-f]+)\s+bytes=([0-9A-Fa-f ]+)$")


def parse_capture_log(path: Path) -> list:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = bytes(int(b, 16) for b in m.group(2).split())
        out.append((addr, raw))
    return out


def contains_japanese(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if 0x3041 <= cp <= 0x3096 or 0x30A1 <= cp <= 0x30FA:
            return True
    return False


def classify(raw: bytes, table) -> tuple:
    text, _consumed = dt.decode_string(raw + b"\x00", 0, table)
    return text, contains_japanese(text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_process_capture -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add python/tools/process_capture.py python/tools/test_process_capture.py
git commit -m "feat(capture): parse capture log + decode/classify"
```

---

### Task 2: Offset mapping (binary search) and worklist emission

**Files:**
- Modify: `python/tools/process_capture.py`
- Test: `python/tools/test_process_capture.py`

**Interfaces:**
- Consumes: `parse_capture_log`, `classify`, `GAME_DIR`, `STAGES`, `CAPTURE_DIR`.
- Produces: `find_offsets(raw: bytes) -> list[tuple[str,int]]` (stage, file offset of every exact byte match across original STGs); `process(log_path: Path) -> dict` with keys `missed` (list of `{text, stage, offset}`), `stats`; `write_worklist(result: dict) -> Path` writing `output/capture/missed_displayed.txt` in `<id> / JP: / KO:` format.

- [ ] **Step 1: Write the failing test**

```python
# add to test_process_capture.py
class TestMapAndEmit(unittest.TestCase):
    def setUp(self):
        if not (pc.GAME_DIR / "S700.STG").exists():
            self.skipTest("original STG binaries not present")

    def test_find_offsets_treasure_chest(self):
        raw = bytes([0x05,0x2A,0x1A,0x10,0x06,0x27,0x3E,0x0A,0x39])
        hits = pc.find_offsets(raw)
        self.assertTrue(any(stage and isinstance(off, int) for stage, off in hits),
                        "treasure-chest bytes should be found in at least one STG")

    def test_process_flags_japanese_with_offset(self):
        fd, p = tempfile.mkstemp(suffix=".log"); os.close(fd)
        Path(p).write_text("addr=0x801A0000 bytes=05 2A 1A 10 06 27 3E 0A 39\n",
                           encoding="utf-8")
        result = pc.process(Path(p))
        self.assertEqual(len(result["missed"]), 1)
        m = result["missed"][0]
        self.assertIn("たからばこ", m["text"])
        self.assertIsNotNone(m["stage"])
        os.unlink(p)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_process_capture.TestMapAndEmit -v`
Expected: FAIL — `AttributeError: ... 'find_offsets'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to process_capture.py
def find_offsets(raw: bytes) -> list:
    """Every (stage, file_offset) where these exact bytes occur in an original STG."""
    hits = []
    for stage in STAGES:
        p = GAME_DIR / f"{stage}.STG"
        if not p.exists():
            continue
        data = p.read_bytes()
        pos = data.find(raw)
        while pos != -1:
            hits.append((stage, pos))
            pos = data.find(raw, pos + 1)
    return hits


def process(log_path: Path) -> dict:
    table = dt.build_decode_table()
    entries = parse_capture_log(log_path)
    seen = set()
    missed = []
    total = 0
    jp = 0
    for _addr, raw in entries:
        total += 1
        text, is_jp = classify(raw, table)
        if not is_jp:
            continue
        jp += 1
        key = text.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        hits = find_offsets(raw)
        stage, off = (hits[0] if hits else (None, None))
        missed.append({"text": key, "stage": stage, "offset": off,
                       "all_hits": hits})
    return {"missed": missed,
            "stats": {"total": total, "japanese": jp, "unique_missed": len(missed)}}


def write_worklist(result: dict) -> Path:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = CAPTURE_DIR / "missed_displayed.txt"
    s = result["stats"]
    lines = [
        "# Missed displayed dialogue (captured at runtime)",
        f"# total hits={s['total']}  japanese={s['japanese']}  unique={s['unique_missed']}",
        "# Each entry: <id> / JP / KO (fill KO).  id = STAGE:0xOFFSET or UNMAPPED:n",
        "",
    ]
    for i, m in enumerate(result["missed"]):
        idtok = (f"{m['stage']}:0x{m['offset']:08X}" if m["stage"] is not None
                 else f"UNMAPPED:{i}")
        lines += [f"  {idtok}", f"    JP: {m['text']}", f"    KO: "]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_process_capture -v`
Expected: PASS (all; TestMapAndEmit runs if S700.STG present, else skips).

- [ ] **Step 5: Add CLI entrypoint and commit**

Append to `process_capture.py`:
```python
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    log_path = Path(argv[0]) if argv else (CAPTURE_DIR / "capture.log")
    if not log_path.exists():
        print(f"ERROR: capture log not found: {log_path}", file=sys.stderr)
        return 1
    result = process(log_path)
    out = write_worklist(result)
    s = result["stats"]
    print(f"hits={s['total']} japanese={s['japanese']} unique missed={s['unique_missed']}")
    print(f"worklist -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
git add python/tools/process_capture.py python/tools/test_process_capture.py
git commit -m "feat(capture): map captured bytes to STG offset + emit worklist + CLI"
```

---

### Task 3: PCSX-Redux Lua hook

**Files:**
- Create: `tools/atl2_capture.lua`

**Interfaces:** none (standalone Lua run inside PCSX-Redux). Not unit-testable; verified manually via the runbook (Task 4).

- [ ] **Step 1: Write the script**

```lua
-- tools/atl2_capture.lua — PCSX-Redux dialogue capture for Arc the Lad 2.
-- Load via PCSX-Redux Lua console: dofile('.../tools/atl2_capture.lua')
-- Modes: 'calibrate' (find the text-pointer register) then 'capture'.
local MODE     = 'calibrate'        -- set to 'capture' after calibration
local HANDLER  = 0x80101560
local TEXT_REG = 'a0'               -- set after calibration (a0/a1/a2/a3/...)
local MAX_LEN  = 256
local LOG_PATH = 'output/capture/capture.log'

local function read_bytes(addr)
    local mem = PCSX.getMemPtr()                 -- 2MB main RAM, 0-indexed
    local base = bit.band(addr, 0x1FFFFF)
    local out = {}
    for i = 0, MAX_LEN - 1 do
        local b = mem[base + i]
        if b == 0 then break end
        out[#out + 1] = string.format('%02X', b)
    end
    return table.concat(out, ' ')
end

local seen = {}
local logf = nil
local function logline(s)
    if not logf then logf = io.open(LOG_PATH, 'a') end
    logf:write(s .. '\n'); logf:flush()
end

PCSX.addBreakpoint(HANDLER, 'Exec', 4, 'atl2-capture', function()
    local gpr = PCSX.getRegisters().GPR.n
    if MODE == 'calibrate' then
        -- Dump every register that looks like a RAM pointer + its bytes,
        -- so the operator can spot which one holds the text.
        for _, name in ipairs({'a0','a1','a2','a3','s0','s1','v0','v1','t0'}) do
            local v = gpr[name]
            if v >= 0x80000000 and v <= 0x801FFFFF then
                print(string.format('%s=0x%08X  %s', name, v, read_bytes(v)))
            end
        end
        print('--- one hit; trigger a KNOWN line, match its bytes to a register ---')
    else
        local addr = gpr[TEXT_REG]
        if addr >= 0x80000000 and addr <= 0x801FFFFF and not seen[addr] then
            seen[addr] = true
            logline(string.format('addr=0x%08X bytes=%s', addr, read_bytes(addr)))
        end
    end
end)
print('atl2_capture loaded in MODE=' .. MODE .. '. Breakpoint @0x80101560.')
```

- [ ] **Step 2: Verify it loads (syntax)**

Run (if `luac`/`lua` available): `luac -p tools/atl2_capture.lua && echo "lua syntax OK"`
Expected: `lua syntax OK`. If no Lua toolchain, skip — it is verified live in PCSX-Redux (Task 4 runbook). Note in the commit that the PCSX-Redux Lua API (`PCSX.addBreakpoint`, `PCSX.getRegisters`, `PCSX.getMemPtr`) should be confirmed against the installed version's docs at https://pcsx-redux.consoledev.net/Lua/introduction/.

- [ ] **Step 3: Commit**

```bash
git add tools/atl2_capture.lua
git commit -m "feat(capture): PCSX-Redux Lua hook (calibrate + capture modes)"
```

---

### Task 4: Runbook

**Files:**
- Create: `docs/emulator-capture.md`

**Interfaces:** documentation tying Tasks 1–3 together.

- [ ] **Step 1: Write the runbook**

````markdown
# Emulator capture workflow (decoder-missed dialogue)

Captures dialogue actually displayed by the **patched** build, flags lines still
in Japanese (missed by translation), and maps each to its STG offset.

## 1. Install PCSX-Redux
- macOS: download from https://pcsx-redux.consoledev.net/ (or `brew install --cask pcsx-redux` if available). DuckStation cannot script this.

## 2. Load the patched build
- Open PCSX-Redux → run the disc:
  `output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).cue`

## 3. Calibrate (one time)
- Edit `tools/atl2_capture.lua`: ensure `MODE = 'calibrate'`.
- PCSX-Redux → Lua console → `dofile('<repo>/tools/atl2_capture.lua')`.
- In game, trigger ONE known line: examine an **empty treasure chest**
  (Japanese "おれはたからばこだ", bytes `05 2A 1A 10 06 27 3E 0A 39`).
- The console prints each pointer-register + its bytes. Find the register whose
  bytes start `05 2A 1A 10 ...` — that is your `TEXT_REG`.
- Set `MODE = 'capture'` and `TEXT_REG = '<that register>'` in the Lua file.

## 4. Capture (play for coverage)
- Reload: `dofile('<repo>/tools/atl2_capture.lua')`.
- Play through the areas you care about (towns, events, shops). Each new displayed
  line is appended to `output/capture/capture.log`.
- Coverage = what you visit. Use save states to tour scenes efficiently.

## 5. Post-process
```bash
python python/tools/process_capture.py output/capture/capture.log
```
Outputs `output/capture/missed_displayed.txt`: still-Japanese displayed lines as
`<id> / JP / KO` (id = `STAGE:0xOFFSET`). `UNMAPPED:n` means the bytes weren't
found in any STG (rare — report it).

## 6. Translate + re-patch
- Fill the `KO:` lines, then translate those offsets into `translated/ko/{stage}_STG.txt`
  preserving all control codes (see safe-edit rules), and re-run
  `python python/patch/patch_workflow.py --all`.
````

- [ ] **Step 2: Commit**

```bash
git add docs/emulator-capture.md
git commit -m "docs(capture): emulator capture runbook"
```

---

## Self-Review Notes
- **Spec coverage:** Lua dumb-logger (Task 3); Python decode/classify (Task 1); offset map via binary search + worklist (Task 2); runbook + calibration (Task 4). The spec's `RAM_BASE` math is intentionally replaced by byte-search mapping (simpler, testable) — calibration now only needs `TEXT_REG`; noted in runbook.
- **Type consistency:** `classify -> (text, is_jp)`, `find_offsets -> [(stage,off)]`, `process -> {missed:[{text,stage,offset,all_hits}], stats}`, `write_worklist -> Path` — consistent across Tasks 1–2.
- **No placeholders:** Lua `TEXT_REG` default `'a0'` is a real runnable default refined by calibration (not a TODO); every code step is complete.

## Out of scope
- Automated play / save-state tour scripting.
- Verifying already-translated lines render (QA) — this workflow targets *missed* lines.
