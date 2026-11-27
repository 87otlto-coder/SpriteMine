"""Private source-named SMB3 PRG1 audio catalog using external Game Music Emu."""
from __future__ import annotations
import argparse
from array import array
from dataclasses import dataclass
import html
import json
import math
from pathlib import Path
from . import smb3_audio as audio

@dataclass(frozen=True)
class Request:
    name: str
    category: str
    queue: int
    value: int
    context: str = ''

# Source symbols in smb3.asm, pinned in audio.SOURCE_REF. IDs are not unique assets.
MAP_MUSIC = ('world_1','world_2','world_3','world_4','world_5','world_6','world_7','world_8',
             'sky_coin_heaven','invincibility','warp_whistle','music_box','throne_room','bonus_game','ending')
LEVEL_MUSIC = ('overworld','underground','underwater','fortress','boss','airship','hammer_bros_battle',
               'toad_house','athletic','p_switch','bowser','world_8_letter')
JINGLES = ('player_death','game_over','boss_victory','world_victory','bowser_fall','course_clear','time_warning')
PLAYER = ('jump','bump','swim_squish','kick','pipe_shrink','fireball','p_meter','frog_hop')
LEVEL1 = ('coin','powerup_rise','vine_rise','cannon_fire','text_blip','powerup','one_up','lost_suit')
REQUESTS = tuple([Request(n,'music',0x4f5,i) for i,n in enumerate(MAP_MUSIC,1)] +
    [Request(n,'music',0x4f5,i*16,'Shares the source sequence with Toad House; in-game context may alter behavior.' if n=='p_switch' else '') for i,n in enumerate(LEVEL_MUSIC,1)] +
    [Request(n,'jingle',0x4f4,1<<i,'Requires previous music state for normal resume behavior.' if n=='time_warning' else '') for i,n in enumerate(JINGLES)] +
    [Request(n,'effect',0x4f1,1<<i,'Repeated requests required for sustained ringing; single request only.' if n=='p_meter' else '') for i,n in enumerate(PLAYER)] +
    [Request(n,'effect',0x4f2,1<<i) for i,n in enumerate(LEVEL1)] +
    [Request(n,'effect',0x4f2,v,'Special request; identity/behavior needs listening review.') for n,v in [('unknown_level1',0x90),('lost_shoe',0xA0),('tail_wag',0xB0)]] +
    [Request(n,'effect',0x4f3,v,'Single request only; sustained gameplay behavior may differ.' if n in ('flame_jet','airship_fly','hammer_bros_march') else '') for n,v in [('crumble',1),('flame_jet',2),('boomerang',4),('airship_fly',8),('hammer_bros_march',16),('skid',128)]] +
    [Request(n,'effect',0x4f6,v) for n,v in [('map_enter_world',1),('map_path_move',2),('map_enter_level',4),('map_inventory_flip',8),('map_bonus_appear',16),('map_denied',128)]] +
    [Request('pause','effect',0x4f7,1),Request('resume','effect',0x4f7,2,'Requires paused state; standalone request may be silent.')])


def adapter(raw: bytes, request: Request, diagnostic: bool = False) -> bytes:
    if audio.sha(raw) != audio.ROM_SHA256:
        raise ValueError('ROM fingerprint mismatch')
    return audio._make_queue_adapter(raw[16:16+262144], request.queue, request.value, diagnostic=diagnostic)


def tail_trim(pcm: array, *, threshold: int = 64, tail_ms: int = 200) -> tuple[array, str]:
    """Preserve onset; trim only after last above-threshold sample plus tail."""
    if len(pcm)%2 or not pcm: raise ValueError('Expected nonempty stereo PCM')
    last = next((i//2 for i in range(len(pcm)-1,-1,-1) if abs(pcm[i])>threshold), -1)
    if last < 0: return pcm[:0], 'no signal above threshold'
    end = min(len(pcm)//2,last+1+audio.RATE*tail_ms//1000)
    return pcm[:2*end], 'bounded render; activity near end' if end == len(pcm)//2 else 'audible tail trimmed'


def render_request(raw: bytes, gme: audio.GME, request: Request, out: Path) -> dict:
    n = adapter(raw, request)
    result = {'name':request.name,'category':request.category,'queue':request.queue,'value':request.value,
              'context':request.context,'nsf_sha256':audio.sha(n),'exports':[]}
    def save(suffix: str, pcm: array):
        info=audio.write_wav(out/f'{request.name}_{suffix}.wav',pcm)
        info['peak_pcm']=max(map(abs,pcm),default=0)
        result['exports'].append(info)
    if request.category=='music':
        d=adapter(raw,request,True)
        markers=audio.marker_positions(gme.render(d,120,mute_mask=0x1e))
        if len(markers)<3: markers=audio.marker_positions(gme.render(d,300,mute_mask=0x1e))
        result['diagnostic_nsf_sha256']=audio.sha(d)
        try: loop=audio.select_loop(markers)
        except ValueError as e:
            result.update(status='loop unresolved; preview only',diagnostic_error=str(e),markers_samples=markers)
            save('preview',gme.render(n,60)); return result
        start,end=loop['start_sample'],loop['end_sample']
        if not 0<=start<end<=300*audio.RATE: raise ValueError('Loop exceeds bounded render')
        pcm=gme.render(n,math.ceil(end/audio.RATE))
        save('loop',pcm[start*2:end*2])
        if markers[0] > audio.RATE//10: save('intro_and_first_cycle',pcm[:start*2])
        result.update(status='source-marker loop; listening review pending',loop=loop)
    else:
        pcm,status=tail_trim(gme.render(n,20 if request.category=='jingle' else 8))
        result['status']=status
        if pcm: save('isolated',pcm)
    return result


def make_index(out: Path, manifest: dict) -> None:
    rows=[]
    for entry in manifest['requests']:
        name=html.escape(entry['name'].replace('_',' ').title())
        files=''.join(f'<div><a href="{html.escape(e["file"],quote=True)}">{html.escape(e["file"])}</a> · {e["seconds"]:.3f}s · full-scale samples {e["full_scale_samples"]}<br><audio controls preload="none" src="{html.escape(e["file"],quote=True)}" {"loop" if e["file"].endswith("_loop.wav") else ""}></audio></div>' for e in entry['exports']+entry.get('stems',[]))
        rows.append(f'<article><h3>{name}</h3><p>{entry["category"]} · ${entry["queue"]:04X}/${entry["value"]:02X} · {html.escape(entry["status"])}</p><p>{html.escape(entry.get("context",""))}</p>{files}</article>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SpriteMine Audio Catalog</title><style>body{background:#14171b;color:#eee;font:16px system-ui;margin:32px auto;max-width:1000px;padding:0 20px}article{border-top:1px solid #41464e;padding:12px 0}a{color:#9dd8ff}p{color:#b9c3ce}audio{width:min(100%,450px);margin:6px 0 12px}</style><h1>SpriteMine · SMB3 audio catalog</h1><p>Private original-ROM emulated renders. Source-marker loops are not exact APU-state equality. Single-request effects may depend on game context. See manifest.json for hashes and limitations.</p>'+''.join(rows)+'</html>'
    (out/'index.html').write_text(page,encoding='utf-8')


def render_stems(raw: bytes, gme: audio.GME, entry: dict, out: Path) -> list[dict]:
    """Solo five internal APU voices using GME's mute mask, not source separation."""
    request = next(r for r in REQUESTS if r.name == entry['name'])
    start,end=entry['loop']['start_sample'],entry['loop']['end_sample']
    n=adapter(raw,request)
    stems=[]
    for i,name in enumerate(('pulse_1','pulse_2','triangle','noise','dmc')):
        mask=0x1f ^ (1<<i)
        pcm=gme.render(n,math.ceil(end/audio.RATE),mute_mask=mask)[start*2:end*2]
        info=audio.write_wav(out/f'{request.name}_solo_{name}.wav',pcm)
        info.update(voice=name,mute_mask=mask,peak_pcm=max(map(abs,pcm),default=0))
        stems.append(info)
    return stems


def export_catalog(rom: Path,out: Path,library: str|None=None,requests=REQUESTS, *, stems: tuple[str,...]=()) -> dict:
    raw=audio.read_rom(rom);gme=audio.GME(library)
    out.mkdir(parents=True,exist_ok=False)
    entries=[]
    for req in requests:
        entry=render_request(raw,gme,req,out)
        entries.append(entry)
        print(f'{req.name}: {entry["status"]}',flush=True)
    for entry in entries:
        if entry['name'] in stems and 'loop' in entry:
            entry['stems']=render_stems(raw,gme,entry,out)
    manifest={'schema':1,'kind':'isolated original-ROM emulation','rom_sha256':audio.sha(raw),'source':audio.SOURCE_REF,
              'sample_rate':audio.RATE,'play_period_us':audio.PERIOD_US,'gme_library':gme.path,'requests':entries,
              'limitations':['One request from reset; context-dependent behavior not established.',
                             'Loop markers quantized to 2ms, with 8ms pre-roll; exact APU phase equality not established.',
                             'Full-scale samples reported, not repaired; individual listening approval pending.',
                             'Source aliases may share identical audio. Not exhaustive gameplay sound coverage.',
                             'Solo voices use GME mute masks; separate PCM files need not sum to the mixed render.']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    make_index(out,manifest)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path);p.add_argument('output',type=Path);p.add_argument('--gme')
    p.add_argument('--only',nargs='+',choices=[r.name for r in REQUESTS])
    p.add_argument('--stems',nargs='+',choices=[r.name for r in REQUESTS if r.category=='music'],default=[])
    args=p.parse_args();export_catalog(args.rom,args.output,args.gme,tuple(r for r in REQUESTS if not args.only or r.name in args.only),stems=tuple(args.stems))

if __name__=='__main__':main()
