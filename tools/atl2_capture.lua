-- tools/atl2_capture.lua — PCSX-Redux dialogue capture for Arc the Lad 2.
-- Load via PCSX-Redux Lua console: dofile('.../tools/atl2_capture.lua')
-- Modes: 'calibrate' (find the text-pointer register) then 'capture'.
-- Switch mode LIVE in the console (no reload): ATL2_MODE='capture'; ATL2_TEXT_REG='a1'
local MODE     = 'calibrate'        -- initial mode on load
local HANDLER  = 0x80101560
local TEXT_REG = 'a0'               -- initial text-pointer register (refine via calibrate)
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

-- MODE / TEXT_REG are exposed as LIVE globals so you can switch without
-- re-loading the script (which would risk stacking breakpoints). To go from
-- calibrate to capture, just run in the Lua console:
--     ATL2_MODE = 'capture' ; ATL2_TEXT_REG = 'a1'   -- (your register)
_G.ATL2_MODE = MODE
_G.ATL2_TEXT_REG = TEXT_REG

-- IMPORTANT (two PCSX-Redux gotchas):
-- 1) Store the breakpoint object persistently or it is garbage-collected and
--    silently removed (an un-stored addBreakpoint "arms" then never fires).
-- 2) Re-running this file must NOT stack duplicate breakpoints. So first remove
--    any prior one (best-effort; :remove may not exist on all versions, hence
--    pcall) and drop the reference, then create exactly one.
if _G.ATL2_BP then
    pcall(function() _G.ATL2_BP:remove() end)
    _G.ATL2_BP = nil
end

local function in_ram(v)  -- true only for a numeric main-RAM pointer
    return type(v) == 'number' and v >= 0x80000000 and v <= 0x801FFFFF
end

-- The hook runs in the CPU breakpoint context; an error here (e.g. a bad live
-- ATL2_TEXT_REG making gpr[reg] nil, then nil>=number) would crash on every hit.
-- So the whole body is wrapped in pcall and every numeric use is type-guarded,
-- and we NEVER return false (that would make PCSX-Redux delete the breakpoint).
_G.ATL2_BP = PCSX.addBreakpoint(HANDLER, 'Exec', 4, 'atl2-capture', function()
    pcall(function()
        local gpr = PCSX.getRegisters().GPR.n
        local mode = _G.ATL2_MODE
        if mode == 'calibrate' then
            for _, name in ipairs({'a0','a1','a2','a3','s0','s1','v0','v1','t0'}) do
                local v = gpr[name]
                if in_ram(v) then
                    print(string.format('%s=0x%08X  %s', name, v, read_bytes(v)))
                end
            end
            print('--- one hit; trigger a KNOWN line, match its bytes to a register ---')
        elseif mode == 'capture' then
            local reg = _G.ATL2_TEXT_REG
            local addr = (type(reg) == 'string') and gpr[reg] or nil
            if in_ram(addr) and not seen[addr] then
                seen[addr] = true
                logline(string.format('addr=0x%08X bytes=%s', addr, read_bytes(addr)))
            end
        end
        -- any other ATL2_MODE value: do nothing (don't fall into capture)
    end)
end)
print('atl2_capture armed. MODE=' .. _G.ATL2_MODE ..
      '  (switch live: ATL2_MODE=\'capture\'; ATL2_TEXT_REG=\'aN\')')
