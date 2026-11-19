-- Passive CPU PPU-register trace for PRG1 World 1-1 bonus-room commit tests.
-- The MESEN CE 2.2.1 NesPpu::WriteRam $2007 writes are latched and applied
-- after a PPU-cycle delay. This records CPU write intent + pre-write PPU state,
-- NOT a claim that data reached CIRAM at the same cycle.
-- Appended to the existing controller replay Lua in the detailed B leg only.
do
    if detailed and os.getenv("SPRITEMINE_PPU_COMMITS") == "1" then
        local log = assert(io.open(output .. "/ppu-registers.tsv", "wb"))
        log:write("sequence\tkind\tframe\tcpu_cycle\tscanline\tppu_cycle\tpoll\tregister\tvalue\tvideo_ram_addr\tbus_addr\ttmp_video_ram_addr\twrite_toggle\tvertical_write\tmirroring_bit\ttileset\n")
        local sequence = 0
        local function observation(kind, address, value)
            if not restored then return end
            local state = emu.getState()
            if not in_window(state) then return end
            local v = assert(state["ppu.videoRamAddr"], "MesenCE missing ppu.videoRamAddr")
            local bus = assert(state["ppu.ppuBusAddress"], "MesenCE missing ppu.ppuBusAddress")
            local tmp = assert(state["ppu.tmpVideoRamAddr"], "MesenCE missing ppu.tmpVideoRamAddr")
            local mmc3 = assert(state["mapper.regA000"], "MesenCE missing mapper.regA000")
            local toggle = state["ppu.writeToggle"]
            local increment = state["ppu.control.verticalWrite"]
            assert(type(toggle) == "boolean" or type(toggle) == "number",
                "MesenCE missing ppu.writeToggle")
            assert(type(increment) == "boolean" or type(increment) == "number",
                "MesenCE missing ppu.control.verticalWrite")
            sequence = sequence + 1
            assert(sequence <= 12000, "Bounded PPU register trace exceeded 12000 records")
            log:write(table.concat({
                sequence, kind, state.frameCount, clock(state),
                state["ppu.scanline"], state["ppu.cycle"], poll,
                address, value, v, bus, tmp,
                (toggle == true or toggle == 1) and 1 or 0,
                (increment == true or increment == 1) and 1 or 0,
                mmc3 & 1, cpu(0x070A)
            }, "\t"), "\n")
        end
        emu.addMemoryCallback(function(address, value)
            local register = 0x2000 + (address & 0x07)
            if register == 0x2000 or register == 0x2005 or
               register == 0x2006 or register == 0x2007 then
                observation("write", register, value)
            end
        end, emu.callbackType.write, 0x2000, 0x3fff)
        -- Reading PPUSTATUS resets the $2005/$2006 write latch. Observe
        -- before this read; no returned value is supplied or modified.
        emu.addMemoryCallback(function(address, value)
            observation("status-read", 0x2002, value)
        end, emu.callbackType.read, 0x2002, 0x2002)
        local boundaries = assert(io.open(output .. "/ppu-ciram-boundaries.tsv", "wb"))
        boundaries:write("frame\tboundary\tcpu_cycle\tmirroring_bit\n")
        -- Physical 2KiB CIRAM, not the 4KiB mirrored PPU nametable view.
        -- These snapshots are B-only and excluded from common A/B/A signatures.
        local function physical_snapshot(which)
            if not restored then return end
            local state = emu.getState()
            if in_window(state) then
                local reg = assert(state["mapper.regA000"], "Missing MMC3 mirroring state")
                save(string.format("ppu-%d-%s-ciram.bin", state.frameCount, which),
                     read_region(0, 2048, emu.memType.nesNametableRam))
                boundaries:write(table.concat({state.frameCount, which,
                    clock(state), reg & 1}, "\t"), "\n")
            end
        end
        emu.addEventCallback(function() physical_snapshot("start") end, emu.eventType.startFrame)
        emu.addEventCallback(function() physical_snapshot("end") end, emu.eventType.endFrame)
        emu.addEventCallback(function() log:close(); boundaries:close() end, emu.eventType.scriptEnded)
    end
end
