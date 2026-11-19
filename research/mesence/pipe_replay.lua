-- Replay a controller log from an existing World 1-1 state. No gameplay writes.
local output = assert(os.getenv("SPRITEMINE_PIPE_OUTPUT"))
local function load(path)
    local file = assert(io.open(path, "rb"))
    local bytes = file:read("*a")
    file:close()
    return bytes
end
local function save(name, bytes)
    local file = assert(io.open(output .. "/" .. name, "wb"))
    assert(file:write(bytes))
    file:close()
end
local inputs = load(assert(os.getenv("SPRITEMINE_PIPE_INPUT")))
assert(#inputs > 0 and #inputs <= 4096, "Expected bounded binary poll masks")
local state = load(assert(os.getenv("SPRITEMINE_PIPE_SLOT")))
local detailed = os.getenv("SPRITEMINE_PIPE_DETAIL") == "1"
local first = assert(tonumber(os.getenv("SPRITEMINE_PIPE_FIRST")))
local last = assert(tonumber(os.getenv("SPRITEMINE_PIPE_LAST")))
assert(first <= last and last - first <= 120, "Expected bounded capture window")
local log = assert(io.open(output .. "/trace.tsv", "wb"))
local bus = assert(io.open(output .. "/controller.tsv", "wb"))
local events = detailed and assert(io.open(output .. "/events.tsv", "wb"))
local restored, poll, requested = false, 0, {}
local checkpoint_armed = false
local function cpu(address)
    return emu.read(address, emu.memType.nesDebug)
end
local function read_region(base, size, memory)
    local data = {}
    for i = 0, size - 1 do data[i + 1] = string.char(emu.read(base + i, memory)) end
    return table.concat(data)
end
local function clock(s)
    return assert(s["cpu.cycleCount"])
end
local function in_window(s)
    return s.frameCount >= first and s.frameCount <= last
end
local function stamp(s, kind, address, value)
    events:write(string.format("%s\t%d\t%d\t%d\t%d\t%d\t%d\n", kind, s.frameCount,
        clock(s), s["ppu.scanline"], s["ppu.cycle"], address, value))
end

emu.addMemoryCallback(function()
    if not restored then
        restored = assert(emu.loadSavestate(state))
    elseif checkpoint_armed then
        checkpoint_armed = false
        local s = emu.getState()
        stamp(s, "checkpoint", 0, poll)
        save("checkpoint.mss", emu.createSavestate())
        save("screen8.bin", read_region(0x6000 + 8 * 432, 432, emu.memType.nesDebug))
    end
end, emu.callbackType.exec, 0, 0xffff)
emu.addMemoryCallback(function()
    if restored then emu.setInput(requested, 0) end
end, emu.callbackType.write, 0x4016, 0x4016)
emu.addMemoryCallback(function(address, value)
    if restored then
        bus:write(poll, "\t", address, "\t", value & 1, "\n")
    end
end, emu.callbackType.read, 0x4016, 0x4017)
emu.addEventCallback(function()
    if not restored then return end
    poll = poll + 1
    local mask = assert(inputs:byte(poll), "Input exhausted")
    requested = emu.getInput(0)
    for key in pairs(requested) do requested[key] = false end
    requested.right, requested.left = mask & 1 ~= 0, mask & 2 ~= 0
    requested.down, requested.up = mask & 4 ~= 0, mask & 8 ~= 0
    requested.a, requested.b = mask & 16 ~= 0, mask & 32 ~= 0
    requested.start, requested.select = mask & 64 ~= 0, mask & 128 ~= 0
    emu.setInput(requested, 0)
    local s = emu.getState()
    log:write(table.concat({poll, s.frameCount, clock(s), mask,
        cpu(0x75)*256+cpu(0x90), cpu(0x87)*256+cpu(0xa2),
        cpu(0x571), cpu(0x3de), cpu(0x3df), cpu(0x84), cpu(0x85),
        cpu(0xee), cpu(0xef), cpu(0x58e)}, "\t"), "\n")
end, emu.eventType.inputPolled)

local function boundary(kind)
    if not restored then return end
    local s = emu.getState()
    if detailed and kind == "start" and s.frameCount == first then
        checkpoint_armed = true
    end
    if in_window(s) then
        local prefix = s.frameCount .. "-" .. kind
        local tile_mem = read_region(0x6000, 864, emu.memType.nesDebug)
        save(prefix .. "-tiles.bin", tile_mem)
        if detailed then
            stamp(s, kind, 0, 0)
            save(prefix .. "-oam.bin", read_region(0, 256, emu.memType.nesSpriteRam))
            save(prefix .. "-shadow.bin", read_region(0x200, 256, emu.memType.nesDebug))
            save(prefix .. "-ppu.bin", read_region(0, 0x3000, emu.memType.nesPpuDebug))
            save(prefix .. "-palette.bin", read_region(0, 32, emu.memType.nesPaletteRam))
            local fields = {}
            for key, value in pairs(s) do
                if key:match("^ppu%.") and (type(value) == "number" or type(value) == "boolean") then
                    fields[#fields + 1] = key .. "=" .. tostring(value)
                end
            end
            table.sort(fields)
            save(prefix .. "-ppu-state.txt", table.concat(fields, "\n"))
        end
        if kind == "end" then
            local rgb = {}
            for i, color in ipairs(emu.getScreenBuffer()) do
                rgb[i] = string.char((color >> 16) & 255, (color >> 8) & 255, color & 255)
            end
            save(prefix .. "-rgb.bin", table.concat(rgb))
        end
    end
    if kind == "end" and poll >= #inputs then
        log:close()
        bus:close()
        if detailed then events:close() end
        emu.stop(0)
    end
end
emu.addEventCallback(function() boundary("start") end, emu.eventType.startFrame)
emu.addEventCallback(function() boundary("end") end, emu.eventType.endFrame)
if detailed then
    local function record(kind, address, value)
        if restored then
            local s = emu.getState()
            if in_window(s) then stamp(s, kind, address, value) end
        end
    end
    emu.addEventCallback(function() record("irq", 0, 0) end, emu.eventType.irq)
    emu.addEventCallback(function() record("nmi", 0, 0) end, emu.eventType.nmi)
    emu.addMemoryCallback(function(address, value)
        record("mapper-write", address, value)
    end, emu.callbackType.write, 0x8000, 0xffff)
    emu.addMemoryCallback(function(address, value)
        record("pipe-write", address, value)
    end, emu.callbackType.write, 0x571, 0x571)
    -- Bank $1E, immediately after JSR LevelLoad_ByTileset and before
    -- Sprite_RAM_Clear. Confirm the original PRG1 call and successor bytes.
    emu.addMemoryCallback(function()
        if restored and read_region(0x899d, 9, emu.memType.nesDebug) ==
            string.char(0x20, 0x1d, 0x9a, 0x20, 0x84, 0xfd, 0x20, 0x1b, 0x95) then
            local s = emu.getState()
            if in_window(s) then
                stamp(s, "layout-complete", 0x89a0, cpu(0x3df))
                save(s.frameCount .. "-" .. clock(s) .. "-layout-complete.bin",
                    read_region(0x6000, 864, emu.memType.nesDebug))
            end
        end
    end, emu.callbackType.exec, 0x89a0, 0x89a0)
end
