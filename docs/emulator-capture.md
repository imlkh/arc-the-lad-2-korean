# Emulator capture workflow (decoder-missed dialogue)

Captures dialogue actually displayed by the **patched** build, flags lines still
in Japanese (missed by translation), and maps each to its STG offset.

## 1. Install PCSX-Redux
- macOS: download from https://pcsx-redux.consoledev.net/ (or `brew install --cask pcsx-redux` if available). DuckStation cannot script this.

## 2. Load the patched build
- Open PCSX-Redux → run the disc:
  `output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).cue`

## 3. Calibrate (one time)
- PCSX-Redux → Lua console → `dofile('<repo>/tools/atl2_capture.lua')` (loads in
  `calibrate` mode). You should see `atl2_capture armed. MODE=calibrate`.
- In game, trigger ONE known line: examine an **empty treasure chest**
  (Japanese "おれはたからばこだ", bytes `05 2A 1A 10 06 27 3E 0A 39`).
- The console prints each pointer-register + its bytes. Find the register whose
  bytes start `05 2A 1A 10 ...` — that is your text-pointer register.

## 4. Capture (play for coverage)
- Switch to capture mode **live in the console** (no reload — reloading can stack
  breakpoints), substituting the register you found:
  ```lua
  ATL2_MODE = 'capture'; ATL2_TEXT_REG = 'a1'
  ```
- Play through the areas you care about (towns, events, shops). Each new displayed
  line is appended to `output/capture/capture.log`.
- Coverage = what you visit. Use save states to tour scenes efficiently.
- Only re-`dofile` the script if you reset the game (which clears the breakpoint);
  the script removes its prior breakpoint on reload so this won't duplicate.

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

## Troubleshooting: breakpoint never fires

If `atl2_capture loaded…` prints but no register dump appears when dialogue shows:

1. **Use the interpreter, not the dynarec.** Configuration → Emulation → uncheck
   **Dynarec** (that selects the interpreter). The dynamic recompiler ignores
   breakpoints. Then **reset** the game so the interpreter takes over.
2. **Enable the debugger** (Configuration → Emulation → Enable Debugger).
3. **The breakpoint must be stored or it is garbage-collected.** PCSX-Redux
   removes a breakpoint whose returned object is GC'd; `atl2_capture.lua` keeps it
   alive in `_G.ATL2_BP`. A bare `PCSX.addBreakpoint(...)` (no assignment) will
   "arm" then silently never fire.
4. Reliable order after any change: **set interpreter → reset → re-`dofile` the
   script → trigger dialogue.**

Quick self-test (paste in the Lua console, trigger a line):
```lua
_G.bptest = PCSX.addBreakpoint(0x80101560, 'Exec', 4, 't', function() print('FIRED') end)
```
If `FIRED` prints, breakpoints work; load the real script.
