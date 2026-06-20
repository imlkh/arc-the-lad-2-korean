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
