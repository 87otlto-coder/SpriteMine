-- Observation-only MesenCE 2.2.1 adjunct. Native execution NOT yet verified.
-- Concatenate BETWEEN graphics_replay.lua and spritemine_render_probe.lua.
-- Existing replay owns state restoration, input and termination. This code
-- never sets memory/input/state and never returns a replacement callback value.
do
    local first = tonumber(os.getenv("SPRITEMINE_RUNTIME_FIRST") or "448380")
    local last = tonumber(os.getenv("SPRITEMINE_RUNTIME_LAST") or "448408")
    assert(first and last and first == math.floor(first) and last == math.floor(last))
    assert(first >= 0 and last >= first and last-first < 64, "Bounded frame window required")
    local folder = assert(os.getenv("SPRITEMINE_CAPTURE_DIR"))
    local name = folder .. "/runtime-observations.jsonl"
    local previous = io.open(name, "rb")
    if previous then previous:close(); error("Runtime observations already exist") end
    local output = assert(io.open(name, "wb"))
    local count, bytes, dropped, closed = 0, 0, 0, false
    local instruction = nil
    local watched = {}
    -- CANDIDATE identities from Southbird's gameplay RAM declarations.
    -- Capture numeric addresses; do not label runtime values as verified states.
    for _, address in ipairs({0x75,0x87,0x90,0xa2,0xab,0xb4,0xbd,0xcf,
        0xd8,0xec,0xed,0xee,0xef,0xfd,0x12,0x542,0x543,0x574,0x58e,
        0x74d,0x75f,0x4f1,0x4f2,0x4f3,0x4f4,0x4f5}) do watched[address]=true end

    local function json(v)
        if type(v)=="number" then
            assert(v==v and v~=math.huge and v~=-math.huge, "Nonfinite observation")
            if math.type(v)=="integer" then return tostring(v) end
            return string.format("%.17g",v)
        end
        if type(v)=="boolean" then return v and "true" or "false" end
        if type(v)=="string" then
            return '"' .. v:gsub('[%z\1-\31\\"]',function(c)
                return string.format('\\u%04x',string.byte(c))
            end) .. '"'
        end
        if type(v)=="table" then
            local keys, fields = {}, {}
            for key in pairs(v) do keys[#keys+1]=key end
            table.sort(keys)
            for _,key in ipairs(keys) do fields[#fields+1]=json(tostring(key)) .. ':' .. json(v[key]) end
            return '{' .. table.concat(fields,',') .. '}'
        end
        error("Unsupported observation type")
    end
    local function emit(record)
        if closed then return end
        local line=json(record) .. "\n"
        if count >= 10000 or bytes + #line > 8*1024*1024 then dropped=dropped+1; return end
        output:write(line); count=count+1; bytes=bytes+#line
    end
    local function current()
        local state=emu.getState()
        if state.frameCount < first or state.frameCount > last then return nil end
        return state
    end
    local function stamp(state,kind)
        return {kind=kind,frame=state.frameCount,masterClock=state.masterClock,
            clockRate=state.clockRate,region=state.region,
            cpu_cycle_count=state["cpu.cycleCount"],
            scanline=state["ppu.scanline"],cycle=state["ppu.cycle"]}
    end
    local function memory_hex(address,size,memType)
        local values={}
        for i=0,size-1 do values[#values+1]=string.format("%02x",emu.read(address+i,memType)) end
        return table.concat(values)
    end
    local function snapshot(kind)
        local state=current(); if not state then return end
        local record=stamp(state,kind)
        record.ram_hex=memory_hex(0,2048,emu.memType.nesDebug)
        record.oam_hex=memory_hex(0,256,emu.memType.nesSpriteRam)
        record.secondary_oam_hex=memory_hex(0,32,emu.memType.nesSecondarySpriteRam)
        record.palette_hex=memory_hex(0,32,emu.memType.nesPaletteRam)
        record.state=state
        emit(record); output:flush()
    end
    emit({kind="header",schema="spritemine.smb3.runtime-observer/1",first=first,last=last,
        observation="unverified native instrumentation",write_callback_phase="before write",
        clock_unit="NES CPU cycles; API masterClock truncated to uint32"})
    emu.addMemoryCallback(function(address)
        local state=current(); if not state then instruction=nil; return end
        local mapping=emu.convertAddress(address,emu.memType.nesMemory)
        instruction={cpu_address=address,masterClock=state.masterClock,frame=state.frameCount,
            opcode_hex=memory_hex(address,math.min(3,65536-address),emu.memType.nesDebug)}
        if mapping then instruction.mapping=mapping end
    end,emu.callbackType.exec,0,0xffff)
    local function write(address,value)
        if not (watched[address] or (address>=0x200 and address<=0x2ff)
            or (address>=0x4000 and address<=0x4017)
            or address==0x8000 or address==0x8001 or address==0xc000
            or address==0xc001 or address==0xe000 or address==0xe001) then return end
        local state=current(); if not state then return end
        local record=stamp(state,"write")
        record.address=address; record.value=value
        record.instruction=instruction -- actual exec callback address, not assumed cpu.pc
        emit(record)
    end
    emu.addMemoryCallback(write,emu.callbackType.write,0,0xffff)
    emu.addMemoryCallback(function(address,value)
        local state=current(); if not state then return end
        local record=stamp(state,"controller_read")
        record.address=address; record.value=value; emit(record)
    end,emu.callbackType.read,0x4016,0x4017)
    emu.addEventCallback(function() snapshot("startFrame") end,emu.eventType.startFrame)
    emu.addEventCallback(function() snapshot("endFrame") end,emu.eventType.endFrame)
    emu.addEventCallback(function()
        if closed then return end
        -- Footer bypasses the event cap so truncation is always explicit.
        output:write(json({kind="footer",records=count,dropped=dropped,
            integrity=(dropped==0 and "not_overflowed" or "TRUNCATED")}) .. "\n")
        output:close(); closed=true
    end,emu.eventType.scriptEnded)
end
