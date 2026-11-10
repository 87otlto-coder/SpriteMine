-- Loaded by the Windows graphics harness in a fresh headless MesenCE process.
local folder = assert(os.getenv("SPRITEMINE_CAPTURE_DIR"))
local mode = assert(os.getenv("SPRITEMINE_INPUT_PLAN"))
local delay = assert(tonumber(os.getenv("SPRITEMINE_WARMUP")))
local settle = 60
local startPulse = os.getenv("SPRITEMINE_START_PULSE") == "1"
local loaded, frames, polls = false, 0, 0
local state = assert(io.open(assert(os.getenv("SPRITEMINE_STATE")), "rb"))
local bytes = state:read("*a")
state:close()
local trace = assert(io.open(folder .. "/replay.log", "wb"))

local function log(line)
    trace:write(line .. "\n")
    trace:flush()
end

-- Observe the controller bits that actually reach the NES CPU, independently of getInput().
local bus = assert(io.open(folder .. "/controller-bus.log", "wb"))
emu.addMemoryCallback(function(address, value)
    if loaded then bus:write(string.format("%d %04x %d\n", polls, address, value & 1)) end
end, emu.callbackType.read, 0x4016, 0x4017)

-- Reassert at the game's controller strobe as well as the host input poll.
local requested = {}
emu.addMemoryCallback(function()
    for port, keys in pairs(requested) do emu.setInput(keys, port) end
end, emu.callbackType.write, 0x4016, 0x4016)

local function restore()
    if loaded then return end
    loaded = emu.loadSavestate(bytes)
    if not loaded then
        log("restore failed")
        emu.stop(2)
        return
    end
    local s = emu.getState()
    log(string.format("restore %d %d", s.frameCount, s.masterClock))
end
emu.addMemoryCallback(restore, emu.callbackType.exec, 0, 0xffff)

emu.addEventCallback(function()
    if not loaded then return end
    polls = polls + 1
    local history = {}
    for port = 0, 1 do
        local keys = emu.getInput(port)
        for name, value in pairs(keys) do
            assert(type(value) == "boolean", "Only standard controllers supported")
            keys[name] = port == 0 and polls > settle and ((name == "right" and mode == "right")
                or (name == "a" and mode == "jump" and polls <= settle + 6))
            if port == 0 and name == "start" and startPulse and polls == 4 then keys[name] = true end
        end
        assert(port ~= 0 or keys.a ~= nil, "Missing NES controller")
        requested[port] = keys
        emu.setInput(keys, port)
        local observed = emu.getInput(port)
        local buttons = {}
        for name, expected in pairs(keys) do
            assert(observed[name] == expected, "Input override failed")
            buttons[#buttons + 1] = name .. "=" .. tostring(expected)
        end
        table.sort(buttons)
        history[#history + 1] = table.concat(buttons, ",")
    end
    local pose = {}
    for _, index in ipairs({10, 11}) do
        for offset = 0, 3 do
            pose[#pose + 1] = tostring(emu.read(index * 4 + offset, emu.memType.nesSpriteRam))
        end
    end
    log("oam " .. table.concat(pose, ","))
    log(string.format("poll %d %d %s", polls, emu.getState().masterClock,
        table.concat(history, "|")))
end, emu.eventType.inputPolled)

-- The probe calls this hook at startFrame before its first snapshot.
function spritemineReplayReady()
    if not loaded then return false end
    frames = frames + 1
    return frames > settle + delay and polls > settle
end

local boundary = 0
function spritemineReplayBoundary()
    boundary = boundary + 1
    local file = assert(io.open(folder .. "/context" .. boundary .. ".bin", "wb"))
    local data = {}
    for addr = 0x2000, 0x2fff do
        data[#data + 1] = string.char(emu.read(addr, emu.memType.nesPpuDebug))
    end
    file:write(table.concat(data))
    local fields = {}
    for key, value in pairs(emu.getState()) do
        if key:match("^ppu%.") and (type(value) == "number" or type(value) == "boolean") then
            fields[#fields + 1] = key .. "=" .. tostring(value)
        end
    end
    table.sort(fields)
    file:write(table.concat(fields, "\n"))
    file:close()
end

function spritemineReplayComplete()
    log("complete")
    bus:close()
    trace:close()
    emu.stop(0)
end
