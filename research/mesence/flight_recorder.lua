-- Passive NES recorder for MesenCE 2.2.1. No ROM/game addresses or input writes.
local function number(name, default, low, high)
    local n = tonumber(os.getenv("SMFR_" .. name) or default)
    assert(n and n % 1 == 0 and n >= low and n <= high, "Invalid " .. name)
    return n
end
local interval = number("INTERVAL", 30, 1, 3600)
local checkpoint = number("CHECKPOINT", 300, 1, 36000)
local maxFrames = number("FRAMES", 3600, 1, 216000)
local maxBytes = number("MAX_BYTES", 67108864, 1048576, 1073741824)
local eventCap = number("EVENT_CAP", 32, 1, 256)
local eventsEnabled = os.getenv("SMFR_EVENTS") == "1"
local output = assert(os.getenv("SMFR_OUTPUT"), "Set SMFR_OUTPUT to a new directory")
local path = output .. "/capture.jsonl"
local existing = io.open(path, "rb")
if existing then existing:close(); error("Refusing existing capture") end
local file = assert(io.open(path, "wb"))
local bytes, tick, sequence = 0, 0, 0
local closed, forceFull = false, true
local regions, omitted, previous, hooks = {}, {}, {}, {}
local counters = {irq=0, nmi=0}
local burst, totals = {}, {}

local function quote(s)
    return '"' .. s:gsub('[%z\1-\31\\"]', function(c)
        return string.format("\\u%04x", c:byte())
    end) .. '"'
end
local function json(v)
    local t = type(v)
    if t == "string" then return quote(v) end
    if t == "number" or t == "boolean" then return tostring(v) end
    if t ~= "table" then return "null" end
    local parts = {}
    for k, value in pairs(v) do parts[#parts+1] = quote(tostring(k)) .. ":" .. json(value) end
    table.sort(parts)
    return "{" .. table.concat(parts, ",") .. "}"
end
local function write(record)
    local line = json(record) .. "\n"
    if bytes + #line > maxBytes - 1024 then return false end
    assert(file:write(line)); bytes = bytes + #line
    return true
end
local function removeHooks()
    for kind, id in pairs(hooks) do
        emu.removeMemoryCallback(id, emu.callbackType[kind], 0, 0xffff)
    end
    hooks = {}
end
local function finish(reason)
    if closed then return end
    removeHooks()
    -- Reserved footer space keeps the disk budget a hard bound.
    assert(file:write(json({type="end", reason=reason, ticks=tick, samples=sequence,
        pending_events_discarded=next(burst) ~= nil}) .. "\n"))
    file:close(); closed = true
    if os.getenv("SMFR_STOP") == "1" then emu.stop(0) end
end
local function stamp(s)
    return {frame=s.frameCount, cpu_cycle=s["cpu.cycleCount"],
        scanline=s["ppu.scanline"], ppu_cycle=s["ppu.cycle"], tick=tick}
end
local function arm()
    if not eventsEnabled then return end
    burst, totals = {}, {write=0, exec=0}
    for _, kind in ipairs({"write", "exec"}) do
        local retained = 0
        hooks[kind] = emu.addMemoryCallback(function(address, value)
            totals[kind] = totals[kind] + 1
            if retained < eventCap then
                retained = retained + 1
                local event = stamp(emu.getState())
                event.address, event.value, event.kind = address, value, kind
                burst[kind .. retained] = event
            end
            -- Never return a value: returning an integer would modify execution.
        end, emu.callbackType[kind], 0, 0xffff)
    end
end
local initial = emu.getState()
assert(initial.consoleType == "Nes", "Initial proof of concept supports NES only")
local memoryBudget = 262144
local names = {}
for name in pairs(emu.memType) do
    if name:match("^nes.*Ram$") then names[#names+1] = name end
end
table.sort(names)
for _, name in ipairs(names) do
    local ok, size = pcall(emu.getMemorySize, emu.memType[name])
    if ok and size > 0 and size <= memoryBudget then
        regions[name] = {size=size, memory=emu.memType[name]}
        memoryBudget = memoryBudget - size
    else omitted[name] = ok and (size == 0 and "empty" or "memory budget") or "unavailable" end
end
-- Mapped pattern + nametable view: captures bank-view changes, not fetch-time banks.
regions.nesPpuDebug = {size=0x3000, memory=assert(emu.memType.nesPpuDebug)}
assert(write({type="header", schema=1, evidence="captured", rom=emu.getRomInfo(),
    interval=interval, checkpoint=checkpoint, max_frames=maxFrames, max_bytes=maxBytes,
    event_cap=eventCap, event_mode=eventsEnabled and "one-frame-bursts" or "off",
    regions=regions, omitted=omitted, state=initial}))
file:flush()
local function snapshot(s)
    local full = forceFull or (tick - 1) % checkpoint < interval
    local data, changed = {}, {}
    for name, region in pairs(regions) do
        local pages, count = {}, 0
        local old = previous[name] or {}
        for offset = 0, region.size - 1, 256 do
            local chars = {}
            for address = offset, math.min(offset+255, region.size-1) do
                chars[#chars+1] = string.char(emu.read(address, region.memory))
            end
            local page = table.concat(chars)
            local prior = old[offset]
            if prior then
                for i=1,#page do if page:byte(i) ~= prior:byte(i) then count=count+1 end end
            else count=count+#page end
            if full or page ~= prior then
                pages[tostring(offset)] = (page:gsub(".", function(c) return string.format("%02x", c:byte()) end))
            end
            old[offset] = page
        end
        previous[name], data[name], changed[name] = old, pages, count
    end
    sequence = sequence + 1
    local ok = write({type="sample", seq=sequence, full=full, time=stamp(s), state=s,
        input=emu.getInput(0), memory=data, changed_bytes=changed, interrupts=counters,
        events=burst, event_totals=totals})
    burst, totals = {}, {}
    forceFull = false
    file:flush()
    if not ok then sequence=sequence-1; finish("byte_limit") end
end
for _, kind in ipairs({"irq", "nmi"}) do
    emu.addEventCallback(function() if not closed then counters[kind]=counters[kind]+1 end end, emu.eventType[kind])
end
for _, kind in ipairs({"reset", "stateLoaded"}) do
    emu.addEventCallback(function() forceFull=true end, emu.eventType[kind])
end
emu.addEventCallback(function()
    if closed then return end
    tick = tick + 1
    local s = (next(hooks) or forceFull or (tick-1) % interval == 0) and emu.getState()
    if next(hooks) then
        removeHooks()
        if not write({type="burst", time=stamp(s), events=burst, event_totals=totals}) then
            burst, totals = {}, {}; finish("byte_limit"); return
        end
        burst, totals = {}, {}
    end
    if forceFull or (tick-1) % interval == 0 then snapshot(s); if not closed then arm() end end
    if tick >= maxFrames then finish("frame_limit") end
end, emu.eventType.endFrame)
emu.addEventCallback(function() finish("script_ended") end, emu.eventType.scriptEnded)
