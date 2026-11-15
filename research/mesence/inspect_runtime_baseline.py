"""Read existing private evidence without launching an emulator or writing files."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .animation_archive import read_verified_timeline, verified_timeline_runs
from .player_recipe import read_recipe
from .level_header import read_world_1_1


def inspect(timeline_file: Path, *, revalidate_sources: bool = False) -> dict:
    timeline = read_verified_timeline(timeline_file)
    if revalidate_sources:
        verified_timeline_runs(timeline_file)
    rom = Path(timeline['frames'][0]['run_dir'])/'replay.nes'
    # A recipe correspondence is not a CPU-observed Player_Frame identity.
    candidates = [read_recipe(rom, i) for i in (0x3e,0x3f,0x40)]
    observations=[]
    for frame in timeline['frames']:
        folder=Path(frame['run_dir'])/'A'
        manifests=list(folder.glob('render_*.json'))
        if len(manifests)!=1: raise ValueError('Expected one source render manifest')
        manifest=json.loads(manifests[0].read_text(encoding='utf-8'))
        boundary=manifest['phase_captures'][2]
        oam=(folder/boundary['files']['oam']).read_bytes()
        if len(oam)!=256: raise ValueError('Truncated source OAM')
        selected=[list(oam[i*4:i*4+4]) for i in range(10,16)]
        matches=[]
        for recipe in candidates:
            tiles=[c['tile_id'] for c in recipe['components']]
            # Restricted to this archive's horizontally flipped small-player case.
            predicted=[tiles[4],tiles[3],tiles[5],tiles[1],tiles[0],tiles[2]]
            if predicted == [x[1] for x in selected]: matches.append(recipe['frame'])
        if len(matches)!=1: raise ValueError('No unique supported recipe correspondence')
        if any(x[2]!=0x40 for x in selected): raise ValueError('Unsupported captured attributes')
        if any(selected[i][0]!=0xf8 for i in range(2,6)):
            raise ValueError('Expected suppressed components at offscreen Y')
        recipe=next(r for r in candidates if r['frame']==matches[0])
        # Small suit root page $50 is a source hypothesis, tested here against
        # independently verified physical CHR offsets for each visible component.
        bank=0x50+recipe['chr_page_offset']
        expected_offsets=[[0x40010+bank*1024+(tile & 0xfe)*16,
                           0x40010+bank*1024+(tile & 0xfe)*16+16]
                          for tile in frame['tile_ids']]
        if expected_offsets!=frame['source_rom_tile_offsets']:
            raise ValueError('Recipe CHR hypothesis disagrees with verified physical tile offsets')
        raw=(folder/'context3.bin').read_bytes()
        fields=dict(line.split('=',1) for line in raw[4096:].decode().splitlines())
        temporary=int(fields['ppu.tmpVideoRamAddr']); fine_x=int(fields['ppu.xScroll'])
        observations.append({
            'frame':frame['frame_count'], 'candidate_recipe':matches[0],
            'position_x':frame['position_x'],'position_y':frame['position_y'],
            'all_six_oam_tile_ids_match':True,'suppressed_components':4,
            'candidate_chr_1k_bank_matches_source_offsets':bank,
            'temporary_scroll_x':(temporary & 31)*8+fine_x+((temporary>>10)&1)*256,
            'temporary_scroll_y':((temporary>>5)&31)*8+((temporary>>12)&7),
            'rgba_sha256':frame['rgba_sha256'],
            'context_sha256':hashlib.sha256(raw).hexdigest(),
        })
    return {
        'schema':'spritemine.smb3.runtime-baseline-analysis/1',
        'timeline_sha256':hashlib.sha256(timeline_file.read_bytes()).hexdigest(),
        'frames':len(observations), 'source_windows_revalidated':revalidate_sources,
        'oam_tile_fields_compared':len(observations)*6,
        'observations':observations,'world_1_1':read_world_1_1(rom),
        'limitations':['No CPU RAM snapshots or instruction execution evidence in historical captures',
                       'Recipe IDs are source-backed candidates, not observed Player_Frame values',
                       'PPU temporary scroll is not assumed to be world camera coordinates',
                       'Only explicit OAM slots 10 through 15 in this archive are checked']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline',type=Path)
    parser.add_argument('--revalidate-sources',action='store_true')
    args=parser.parse_args()
    print(json.dumps(inspect(args.timeline,revalidate_sources=args.revalidate_sources),indent=2,sort_keys=True))


if __name__=='__main__': main()
