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
