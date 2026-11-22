"""Compare a private MesenCE recording frame to a source-built panorama.

This is *not* a lossless native RGB24 acceptance test: H.264 video compression
adds small RGB errors. Keep independent video frames and captures out of GitHub.
The frame rectangle and measured world origin are explicit and required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def compare(preview_path: Path, frame_path: Path, *, frame_rect: tuple[int,int,int,int],
            world_origin: tuple[int,int], scale: int = 2,
            excluded_rects: tuple[tuple[int,int,int,int], ...] = (),
            tolerance: int = 50) -> dict:
    """Score decompressed video against lossless scene, excluding moving UI.

    The score is **not** native pixel verification: changes caused by encoding
    can be misclassified even with an L-infinity RGB tolerance.
    excluded_rects are in *native 1x frame-rect-local* coordinates.
    """
    if scale < 1 or tolerance < 0 or tolerance > 255:
        raise ValueError('Invalid scale/tolerance')
    x, y, w, h = frame_rect
    ox, oy = world_origin
    if w <= 0 or h <= 0 or w % scale or h % scale:
        raise ValueError('Reference crop must have positive scale-aligned dimensions')
    with Image.open(preview_path) as im:
        scene = im.convert('RGB')
    with Image.open(frame_path) as im:
        frame = im.convert('RGB')
    if x < 0 or y < 0 or x+w > frame.width or y+h > frame.height:
        raise ValueError('Reference crop lies outside the frame')
    nw, nh = w//scale, h//scale
    if ox < 0 or oy < 0 or ox+nw > scene.width or oy+nh > scene.height:
        raise ValueError('World crop lies outside the scene')
    # BOX averages compression noise over the scale-by-scale capture footprint.
    ref = frame.crop((x,y,x+w,y+h)).resize((nw,nh),Image.Resampling.BOX)
    candidate = scene.crop((ox,oy,ox+nw,oy+nh))
    rp, cp = ref.load(), candidate.load()
    ignored = set()
    for rx,ry,rw,rh in excluded_rects:
        if min(rx,ry,rw,rh)<0 or rx+rw>nw or ry+rh>nh:
            raise ValueError('Exclusion rectangle outside native crop')
        ignored.update((i,j) for j in range(ry,ry+rh) for i in range(rx,rx+rw))
    compared = close = 0
    max_abs = 0
    for j in range(nh):
        for i in range(nw):
            if (i,j) in ignored:
                continue
            delta = max(abs(a-b) for a,b in zip(rp[i,j],cp[i,j]))
            max_abs = max(max_abs,delta)
            compared += 1
            close += delta<=tolerance
    return {
        'source_class':'compressed_video_visual_reference_not_lossless_rgb24',
        'candidate_sha256':hashlib.sha256(preview_path.read_bytes()).hexdigest(),
        'reference_sha256':hashlib.sha256(frame_path.read_bytes()).hexdigest(),
        'reference_rect_xywh':list(frame_rect),
        'world_origin_xy':list(world_origin),
        'native_dimensions':[nw,nh],
        'excluded_native_rectangles':[list(r) for r in excluded_rects],
        'max_channel_tolerance':tolerance,
        'compared_positions':compared,
        'within_tolerance':close,
        'outside_tolerance':compared-close,
        'within_tolerance_ratio':round(close/compared,6) if compared else None,
        'scope_limit':'H.264 recording and cursor/player exclusions; no native-verified pixel coverage credited',
    }


def compare_goal_silhouette(preview_path: Path, frame_path: Path, *,
                            frame_rect=(19,65,496,384), world_origin=(2456,239),
                            world_rect=(2472,239,32,155)) -> dict:
    """Compare *classified* black/sky shape along native goal edge.

    This is only an edge silhouette check from a compressed visual reference;
    it does not establish exact colors, object layers or final goal layout.
    """
    x,y,w,h=frame_rect;ox,oy=world_origin; wx,wy,ww,wh=world_rect
    if w%2 or h%2 or min(ww,wh)<=0:
        raise ValueError('Invalid reference size')
    with Image.open(frame_path) as im:
        ref=im.convert('RGB').crop((x,y,x+w,y+h)).resize((w//2,h//2),Image.Resampling.BOX)
    with Image.open(preview_path) as im:
        candidate=im.convert('RGB').crop((wx,wy,wx+ww,wy+wh))
    if (wx-ox)<0 or (wy-oy)<0 or wx-ox+ww>ref.width or wy-oy+wh>ref.height:
        raise ValueError('World rectangle not in aligned reference')
    rp=ref.load();cp=candidate.load()
    samples=match=0
    for j in range(wh):
        for i in range(ww):
            rr,gg,bb=rp[wx-ox+i,wy-oy+j]
            ref_black=(rr<35 and gg<35 and bb<35)
            ref_sky=(rr>145 and gg>160 and bb>160)
            if not (ref_black or ref_sky):
                continue
            cr,cg,cb=cp[i,j]
            same=(ref_black and max(cr,cg,cb)<40) or (ref_sky and cr>150 and cg>190)
            samples+=1;match+=bool(same)
    return {
        'source_class':'compressed_video_black_sky_silhouette_only',
        'world_rect_xywh':list(world_rect),
        'world_origin_xy':list(world_origin),
        'classified_pixels':samples,
        'matching_classes':match,
        'mismatching_classes':samples-match,
        'native_rgb_accepted':False,
        'source_sha256':hashlib.sha256(frame_path.read_bytes()).hexdigest(),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preview',type=Path)
    parser.add_argument('video_frame_png',type=Path)
    parser.add_argument('report',type=Path)
    parser.add_argument('--goal-edge',action='store_true')
    args=parser.parse_args()
    if args.report.exists():
        parser.error('Refusing to overwrite an existing report')
    result=(compare_goal_silhouette(args.preview,args.video_frame_png)
            if args.goal_edge else compare(args.preview,args.video_frame_png,
              frame_rect=(19,65,496,384),world_origin=(2208,239),
              excluded_rects=((148,83,36,40),)))
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
