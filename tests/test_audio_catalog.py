from array import array
import os
from pathlib import Path
import struct
import wave
import pytest
from spritemine import audio_catalog as c
from spritemine import smb3_audio as a


def test_request_coverage():
    from collections import Counter
    assert Counter(r.category for r in c.REQUESTS)=={'music':27,'jingle':7,'effect':33}
    assert len({r.name for r in c.REQUESTS})==67
    assert len({(r.queue,r.value) for r in c.REQUESTS})==67
    assert {r.value for r in c.REQUESTS if r.category=='music'}==set(range(1,16))|set(range(16,193,16))
    assert next(r for r in c.REQUESTS if r.name=='resume').context


def test_queue_adapter():
    prg=b''.join(bytes([i])*8192 for i in range(32))
    for req in c.REQUESTS:
        nsf=a._make_queue_adapter(prg,req.queue,req.value)
        assert nsf[138:143]==bytes([0xa9,req.value,0x8d,req.queue&255,req.queue>>8])
        assert nsf[128+8192:]==b''.join(bytes([i])*8192 for i in a.BANKS)
    with pytest.raises(ValueError): a._make_queue_adapter(prg,0x4f2,1,diagnostic=True)
    with pytest.raises(ValueError): a._make_queue_adapter(prg,0x4f0,1)


def test_tail_trim():
    p=array('h',[0])*2*a.RATE
    p[2000:2002]=array('h',[900,-900])
    cut,status=c.tail_trim(p)
    assert len(cut)//2==1001+9600
    assert status=='audible tail trimmed'
    assert c.tail_trim(array('h',[0])*20)[0]==array('h')
    assert c.tail_trim(array('h',[100])*20)[1]=='bounded render; activity near end'
    with pytest.raises(ValueError): c.tail_trim(array('h',[1]))


def test_index_escapes_metadata(tmp_path):
    c.make_index(tmp_path,{'requests':[{'name':'<test>','queue':0x4f5,'value':1,'category':'music','status':'pending','exports':[]}]})
    assert '&lt;Test&gt;' in (tmp_path/'index.html').read_text(encoding='utf-8')


@pytest.mark.skipif(not (os.getenv('SPRITEMINE_PRIVATE_ROM_ZIP') and os.getenv('SPRITEMINE_GME_LIBRARY')),reason='Private ROM and GME required')
def test_private_catalog_subset(tmp_path):
    req=tuple(r for r in c.REQUESTS if r.name in ('world_1','overworld','coin','resume'))
    one,two=tmp_path/'one',tmp_path/'two'
    args=(Path(os.environ['SPRITEMINE_PRIVATE_ROM_ZIP']),)
    m=c.export_catalog(*args,one,os.environ['SPRITEMINE_GME_LIBRARY'],req,stems=('overworld',))
    n=c.export_catalog(*args,two,os.environ['SPRITEMINE_GME_LIBRARY'],req,stems=('overworld',))
    assert m==n
    assert {p.name:a.sha(p.read_bytes()) for p in one.iterdir()}=={p.name:a.sha(p.read_bytes()) for p in two.iterdir()}
    ov=next(x for x in m['requests'] if x['name']=='overworld')
    assert ov['loop']['inferred_game_ticks']==1536 and len(ov['stems'])==5
    assert all(x['samples_per_channel']==ov['loop']['duration_samples'] for x in ov['stems'])
    assert next(x for x in m['requests'] if x['name']=='resume')['exports']==[]
