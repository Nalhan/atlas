"""Atlas annotation packets, independent reviews, deterministic builds and review sheets.
Run from anywhere: python addons/atlas/tools/annotations.py prepare|check|build|sheets|report
Dependencies are authoring-only: lupa and Pillow. No model/API dependency in the addon.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import math
import struct
from PIL import Image, ImageDraw, ImageFont
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]
ROOT=ADDON.parents[1]
DATA=ADDON/'annotations'
PACKETS=DATA/'packets'
PILOT=[
    ('latheine',102,0,2,'La Theine Plateau','zulkheim'),
    ('valkurm',103,0,3,'Valkurm Dunes','zulkheim'),
    ('konschtat',108,0,8,'Konschtat Highlands','zulkheim'),
    ('selbina',248,0,156,'Selbina','zulkheim'),
    ('ordelle1',193,1,92,"Ordelle's Caves / 1",'zulkheim'),
    ('ordelle2',193,2,93,"Ordelle's Caves / southern galleries",'zulkheim'),
    ('ordelle3',193,14,94,"Ordelle's Caves / apparatus",'zulkheim'),
    ('ordelle4',193,15,95,"Ordelle's Caves / upper",'zulkheim'),
    ('jugner',104,0,4,'Jugner Forest','norvallen'),
    ('batallia',105,0,5,'Batallia Downs','norvallen'),
    ('davoi',149,0,35,'Davoi','norvallen'),
    ('monastic',150,0,36,'Monastic Cavern','norvallen'),
    ('eldieme1',195,14,96,'The Eldieme Necropolis / apparatus','norvallen'),
    ('eldieme2',195,15,97,'The Eldieme Necropolis / entrance','norvallen'),
    ('eldieme3',195,16,98,'The Eldieme Necropolis / crypts','norvallen'),
    ('eldieme4',195,17,99,'The Eldieme Necropolis / lower','norvallen'),
    ('landing1',2,1,241,"Carpenters' Landing / 1",'norvallen'),
    ('landing2',2,2,242,"Carpenters' Landing / 2",'norvallen'),
    ('ranguemont',166,0,65,'Ranguemont Pass','fauregandi'),
    ('beaucedine',111,0,11,'Beaucedine Glacier','fauregandi'),
    ('feiyin1',204,1,117,"Fei'Yin / upper",'fauregandi'),
    ('feiyin2',204,14,118,"Fei'Yin / apparatus",'fauregandi'),
    ('feiyin3',204,15,119,"Fei'Yin / lower",'fauregandi'),
]
JOBS={
    'zulkheim':[m[0] for m in PILOT if m[5]=='zulkheim'],
    'north_east':[m[0] for m in PILOT if m[5] in ('norvallen','fauregandi')],
}
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def plain(value):
    if hasattr(value,'items'):
        items=list(value.items())
        if items and all(isinstance(k,int) for k,_ in items):
            return [plain(value[i]) for i in range(1,len(items)+1)]
        return {k:plain(v) for k,v in items}
    return value
def runtime(binary=False):
    lua=LuaRuntime(unpack_returned_tuples=True,encoding=None if binary else 'utf-8')
    script="package.path=... .. '/?.lua;' ..package.path"
    lua.execute(script.encode() if binary else script,ADDON.as_posix().encode() if binary else ADDON.as_posix())
    return lua
def native_table():
    dll=(ROOT/'SquareEnix/FINAL FANTASY XI/FFXiMain.dll').read_bytes()
    hits=[];start=0
    while True:
        p=dll.find(b'\x64\x00',start)
        if p<0:break
        start=p+1
        if p+42<len(dll) and all(struct.unpack_from('<HB',dll,p+n*14)==(100+n,0) for n in range(3)):
            hits.append(p)
    if len(hits)!=1:raise ValueError('Cannot uniquely identify native map table')
    return dll,hits[0]
def native_map(dll,base,key,zone,floor,index,name,region):
    z,f,_,flags,scale,_,_,offset,ox,oy=struct.unpack_from('<HBBBbbBHhh',dll,base+index*14)
    if (z,f)!=(zone,floor):raise ValueError(f'{key}: native zone/floor mismatch')
    dat={0:5312,1:53295,2:54295}[flags&15]+offset
    return dict(key=key,zone=zone,floor=floor,index=index,dat=dat,name=name,region=region,
        transform=dict(scale=scale,offset_x=ox,offset_y=oy),tab=name.split(' / ')[-1])
def artwork(definition):
    ff=ROOT/'SquareEnix/FINAL FANTASY XI'
    ft=(ff/'FTABLE.DAT').read_bytes();vt=(ff/'VTABLE.DAT').read_bytes();dat=int(definition['dat'])
    packed=struct.unpack_from('<H',ft,dat*2)[0];rom=vt[dat]
    rel=Path('ROM' if rom==1 else f'ROM{rom}')/str(packed>>7)/f'{packed&127}.DAT'
    for overlay in ['horizonoverrides','remapster','xiview','ffxivision']:
        path=ROOT/'polplugins/DATs'/overlay/rel
        if path.exists():return path,overlay,rel
    return ff/rel,'original',rel
def prepare():
    DATA.mkdir(exist_ok=True)
    seed_path=DATA/'seed.json'
    if not seed_path.exists():
        catalog=runtime().eval("require('src.catalog')")
        write(seed_path,dict(schema_version=1,maps=[plain(catalog['maps'][key]) for key in plain(catalog['order'])],
            passages=[dict(plain(p),status='legacy_unreviewed') for _,p in catalog['passages'].items()]))
    seed=read(seed_path);maps={m['key']:m for m in seed['maps']}
    for m in maps.values():m['region']='ronfaure'
    dll,base=native_table()
    for row in PILOT:maps[row[0]]=dict(maps.get(row[0],{}),**native_map(dll,base,*row))
    raw=runtime(True);wrap=raw.eval(b"require('src.dat_image').wrap")
    for key,m in maps.items():
        if not m.get('dat'):continue
        path,overlay,rel=artwork(m);data=path.read_bytes();encoded,w,h=wrap(data)
        if not encoded:raise ValueError(f'{key}: {w}')
        im=Image.open(io.BytesIO(encoded)).convert('RGB');im.thumbnail((1024,1024))
        dest=PACKETS/f'{key}.png';dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest)
        m['artwork']={'sha256':hashlib.sha256(data).hexdigest(),'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest(),'overlay':overlay,
            'path':path.relative_to(ROOT).as_posix(),'image':dest.relative_to(DATA).as_posix(),
            'width':w,'height':h,'reference_size':512}
        original=ROOT/'SquareEnix/FINAL FANTASY XI'/rel
        original_encoded,_,_=wrap(original.read_bytes())
        original_dest=PACKETS/f'{key}-original.png'
        Image.open(io.BytesIO(original_encoded)).convert('RGB').save(original_dest)
        m['artwork']['original_image']=original_dest.relative_to(DATA).as_posix()
    manifest={'schema_version':1,'pilot_maps':[m[0] for m in PILOT],'maps':maps,'jobs':JOBS}
    write(DATA/'manifest.json',manifest)
    for job,keys in JOBS.items():
        write(DATA/'jobs'/f'{job}.json',dict(schema_version=1,job_id=job,maps=keys,
            context=['west','east','tomb1','north','latheine','jugner','ranguemont'],
            contract='CONTRACT.md',manifest='../manifest.json'))
    print(f'Prepared {len(PILOT)} pilot maps; {len(maps)} total map packets')

def coordinate(value,where):
    if not isinstance(value,list) or len(value)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) or n<0 or n>512 for n in value):
        raise ValueError(f'{where}: expected two finite coordinates in 0..512')
def validate_passage(p,maps,where):
    if not isinstance(p.get('id'),str) or not p['id']:raise ValueError(f'{where}: missing ID')
    if p.get('direction') not in ('both','a_to_b'):raise ValueError(f'{where}: invalid direction')
    if p.get('status') or p.get('reviewed'):raise ValueError(f'{where}: worker cannot approve itself')
    for side in ('a','b'):
        e=p.get(side,{})
        if e.get('map') not in maps:raise ValueError(f'{where}/{side}: unknown map')
        for field in ('exit','arrival'):coordinate(e.get(field),f'{where}/{side}/{field}')
        coordinate(e.get('badge',{}).get('at'),f'{where}/{side}/badge')
        badge=e['badge']
        if badge.get('code') is not None and (not isinstance(badge['code'],str) or len(badge['code'])>5):
            raise ValueError(f'{where}/{side}: invalid badge code')
        if type(badge.get('printed')) is not bool:raise ValueError(f'{where}/{side}: printed must be boolean')
        if not isinstance(e.get('component'),str) or not e['component']:raise ValueError(f'{where}/{side}: missing component')
        if math.dist(e['exit'],e['arrival'])>96:raise ValueError(f'{where}/{side}: focus too far from exit')
    if not p.get('evidence'):raise ValueError(f'{where}: evidence is required')
    validate_evidence(p['evidence'],where)
def validate_evidence(evidence_list,where):
    for evidence in evidence_list:
        if not all(evidence.get(k) for k in ('kind','source','detail')):raise ValueError(f'{where}: incomplete evidence')
        if evidence['kind']=='artwork':
            source=Path(evidence['source'])
            path=source if source.is_absolute() else DATA/source
            if not path.exists():raise ValueError(f'{where}: missing artwork evidence {source}')
def corrected(p,decision):
    p=copy.deepcopy(p)
    for key,value in decision.get('corrections',{}).items():
        if key not in ('a','b','direction','note'):raise ValueError(f'Unsupported review correction {key}')
        if key in ('a','b'):
            for field,v in value.items():
                if field not in ('exit','arrival','badge','component','label'):raise ValueError(f'Unsupported endpoint correction {field}')
                if field=='badge':p[key].setdefault(field,{}).update(v)
                else:p[key][field]=v
        else:p[key]=value
    return p
def collect():
    manifest=read(DATA/'manifest.json');maps=manifest['maps'];jobs={}
    for path in sorted((DATA/'candidates').glob('*.json')):
        doc=read(path);job=doc.get('job_id')
        if doc.get('schema_version')!=1 or job not in manifest['jobs'] or job in jobs:
            raise ValueError(f'{path.name}: invalid or duplicate job')
        inventory=doc.get('inventory',[])
        if {item.get('map') for item in inventory}!=set(manifest['jobs'][job]):
            raise ValueError(f'{job}: inventory does not cover assigned maps')
        for item in inventory:
            for endpoint in item.get('exits',[]):coordinate(endpoint.get('exit'),f'{job}/{item["map"]}/inventory')
        ids=set()
        for p in doc.get('passages',[]):
            validate_passage(p,maps,f'{job}/{p.get("id")}')
            if p['id'] in ids:raise ValueError(f'{job}: duplicate passage ID {p["id"]}')
            ids.add(p['id'])
        jobs[job]=(doc,hashlib.sha256(path.read_bytes()).hexdigest())
    review_path=DATA/'reviews/decisions.json'
    review=read(review_path) if review_path.exists() else {}
    decisions={}
    if review:
        if review.get('schema_version')!=1 or not review.get('reviewer'):raise ValueError('Invalid review identity/version')
        if review['reviewer'] in {doc.get('worker') for doc,_ in jobs.values()}:raise ValueError('Worker cannot review its own batch')
        if review.get('candidate_sha256')!={job:v[1] for job,v in jobs.items()}:raise ValueError('Review is stale: candidate fingerprints do not match')
        if review.get('manifest_sha256')!=hashlib.sha256((DATA/'manifest.json').read_bytes()).hexdigest():
            raise ValueError('Review is stale: map manifest changed')
        independent=DATA/review.get('independent_inventory','reviews/independent_inventory.json')
        if not independent.exists():raise ValueError('Independent inventory missing')
        if review.get('independent_inventory_sha256')!=hashlib.sha256(independent.read_bytes()).hexdigest():
            raise ValueError('Review is stale: independent inventory changed')
        image_sources={e['source'] for d in review.get('decisions',[]) if d.get('decision')=='accept'
            for e in d.get('evidence',[]) if e.get('kind')=='artwork'}
        if set(review.get('packet_sha256',{}))!=image_sources:raise ValueError('Review image fingerprint coverage is incomplete')
        for source,expected in review['packet_sha256'].items():
            path=Path(source);path=path if path.is_absolute() else DATA/path
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError(f'Review is stale: artwork changed {source}')
        inventory=read(independent)
        observed={i['map'] for i in inventory.get('inventory',[])}
        if not set(manifest['pilot_maps'])<=observed:raise ValueError('Independent inventory misses pilot maps')
        for d in review.get('decisions',[]):
            pair=(d.get('job_id'),d.get('id'))
            if pair in decisions:raise ValueError(f'Duplicate decision {pair}')
            if d.get('decision') not in ('accept','reject','needs_work') or not d.get('reason'):
                raise ValueError(f'Incomplete review {pair}')
            if pair[0] not in jobs or not any(p['id']==pair[1] for p in jobs[pair[0]][0]['passages']):
                raise ValueError(f'Orphan review {pair}')
            if d['decision']=='accept' and not d.get('evidence'):raise ValueError(f'Accepted record lacks review evidence {pair}')
            validate_evidence(d.get('evidence',[]),str(pair))
            decisions[pair]=d
    accepted=[];stats={'jobs':len(jobs),'pilot_maps':len(manifest['pilot_maps']),'proposed':0,'accepted':0,
        'reject':0,'needs_work':0,'pending':0,'corrected':0,'unresolved':0,'endpoint_correction_pixels':[]}
    for job,(doc,_) in jobs.items():
        stats['unresolved']+=len(doc.get('unresolved',[]))
        for p in doc['passages']:
            stats['proposed']+=1;decision=decisions.get((job,p['id']))
            if not decision:stats['pending']+=1;continue
            status=decision['decision']
            if status!='accept':stats[status]+=1;continue
            result=corrected(p,decision);validate_passage(result,maps,f'review/{job}/{p["id"]}')
            if result.get('uncertainties'):
                # Reviewer must explicitly resolve each concern rather than a
                # generator silently laundering an uncertain worker proposal.
                if not decision.get('resolved_uncertainties'):raise ValueError(f'{p["id"]}: unresolved concerns')
            if decision.get('corrections'):
                stats['corrected']+=1
                stats['endpoint_correction_pixels'] += [round(math.dist(p[s]['exit'],result[s]['exit']),2) for s in ('a','b')]
            result['status']='artwork_reviewed';result['job_id']=job;result['review']=decision
            accepted.append(result);stats['accepted']+=1
    return manifest,jobs,review,accepted,stats
def lua_value(value):
    if value is None:return 'nil'
    if isinstance(value,bool):return str(value).lower()
    if isinstance(value,(int,float)):return repr(value)
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,list):return '{'+','.join(lua_value(v) for v in value)+'}'
    return '{'+','.join('['+lua_value(str(k))+']='+lua_value(v) for k,v in sorted(value.items()))+'}'
def endpoint(e):
    return dict(map=e['map'],x=e['exit'][0],y=e['exit'][1],arrival_x=e['arrival'][0],arrival_y=e['arrival'][1],
        badge_x=e['badge']['at'][0],badge_y=e['badge']['at'][1],code=e['badge']['code'],
        printed=e['badge']['printed'],component=e['component'],label=e.get('label'))
def make_boards(maps,passages):
    by_key={m['key']:m for m in maps};boards={}
    for region in ('zulkheim','norvallen','fauregandi'):
        zones={m['zone'] for m in maps if m['region']==region}
        core=zones.copy()
        for p in passages:
            az,bz=by_key[p['a']['map']]['zone'],by_key[p['b']['map']]['zone']
            if az in core:zones.add(bz)
            if bz in core:zones.add(az)
        groups={z:[m for m in maps if m['zone']==z] for z in sorted(zones)}
        degrees={z:set() for z in zones}
        for p in passages:
            a,b=by_key[p['a']['map']]['zone'],by_key[p['b']['map']]['zone']
            if a in zones and b in zones and a!=b:degrees[a].add(b);degrees[b].add(a)
        center=max(core,key=lambda z:(len(degrees[z]),-z))
        others=sorted(zones-{center},key=lambda z:(z not in degrees[center],z not in core,z))
        nodes={};order=[];by_map={}
        for i,z in enumerate([center]+others):
            key='zone_'+str(z)
            angle=-math.pi/2+(i-1)*2*math.pi/max(1,len(others))
            x,y=(750,560) if i==0 else (750+425*math.cos(angle),560+425*math.sin(angle))
            definitions=groups[z];title=definitions[0]['name'].split(' / ')[0]
            node=dict(key=key,title=title,x=round(x),y=round(y),w=320 if i==0 else 250,h=260 if i==0 else 185,
                maps=[m['key'] for m in definitions],crop=[0.18,0.18,0.84,0.84],external=z not in core)
            nodes[key]=node;order.append(key)
            for m in definitions:by_map[m['key']]=key
        boards[region]=dict(id=region,title=region.upper(),width=1500,height=1120,nodes=nodes,order=order,by_map=by_map)
    return boards
def build():
    manifest,jobs,review,accepted,stats=collect()
    if not review or stats['pending']:raise ValueError('Build requires a final independent decision for every candidate')
    seed=read(DATA/'seed.json');maps=[]
    for key,definition in manifest['maps'].items():
        m={k:v for k,v in definition.items() if k not in ('artwork','transform')}
        m['artwork_sha256']=definition.get('artwork',{}).get('sha256');maps.append(m)
    passages=seed['passages'][:];ids={p['id'] for p in passages}
    for p in sorted(accepted,key=lambda v:(v['job_id'],v['id'])):
        if p['id'] in ids:raise ValueError(f'Accepted ID collides with seed: {p["id"]}')
        pair={p['a']['map'],p['b']['map']}
        for old in passages:
            if {old['a']['map'],old['b']['map']}==pair:
                a,b=(old['a'],old['b']) if old['a']['map']==p['a']['map'] else (old['b'],old['a'])
                if math.dist([a['x'],a['y']],p['a']['exit'])<20 and math.dist([b['x'],b['y']],p['b']['exit'])<20:
                    raise ValueError(f'Accepted passage duplicates existing pair: {p["id"]} / {old["id"]}')
        passages.append(dict(id=p['id'],a=endpoint(p['a']),b=endpoint(p['b']),one_way=p['direction']=='a_to_b',
            note=p.get('note',''),status=p['status'],review_job=p['job_id']))
        ids.add(p['id'])
    result=dict(schema_version=1,maps=maps,passages=passages)
    out=ADDON/'data/catalog.lua';out.parent.mkdir(exist_ok=True)
    content='-- Generated by tools/annotations.py build. Edit annotation sources, not this file.\nreturn '+lua_value(result)+'\n'
    out.write_bytes(content.encode('utf-8'))
    boards=make_boards(maps,passages)
    regions_content='-- Generated pilot layouts; no manual alignment outside Ronfaure.\nreturn '+lua_value(boards)+'\n'
    (ADDON/'data/regions.lua').write_bytes(regions_content.encode('utf-8'))
    write(DATA/'build.json',dict(manifest_sha256=hashlib.sha256((DATA/'manifest.json').read_bytes()).hexdigest(),
        candidate_sha256={job:v[1] for job,v in jobs.items()},review_sha256=hashlib.sha256((DATA/'reviews/decisions.json').read_bytes()).hexdigest(),
        runtime_sha256=hashlib.sha256(content.encode()).hexdigest(),
        regions_sha256=hashlib.sha256(regions_content.encode()).hexdigest(),
        seed_sha256=hashlib.sha256((DATA/'seed.json').read_bytes()).hexdigest(),
        maps=len(maps),passages=len(passages),**stats))
    print(f'Built {len(maps)} maps / {len(passages)} passages; {len(accepted)} independently accepted pilot records')
def sheets():
    manifest,jobs,review,accepted,stats=collect()
    decisions={(d['job_id'],d['id']):d for d in review.get('decisions',[])}
    output=DATA/'sheets';output.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14)
    thumb_font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',12)
    cards=[];links=[]
    for job,(doc,_) in jobs.items():
        for original in doc['passages']:
            decision=decisions.get((job,original['id']),{})
            p=corrected(original,decision)
            card=Image.new('RGB',(1000,420),(23,37,29));d=ImageDraw.Draw(card)
            status=decision.get('decision','pending')
            d.text((12,8),f'{job} / {p["id"]} / {status}',font=font,fill='#e6cea0')
            for i,side in enumerate(('a','b')):
                e=p[side];m=manifest['maps'][e['map']]
                im=Image.open(DATA/m['artwork']['image']).convert('RGB').resize((340,340))
                x=12+i*500;card.paste(im,(x,42));pen=ImageDraw.Draw(card)
                for coord,color,radius in [(e['exit'],'#ff705b',7),(e['arrival'],'#77c9ff',11),(e['badge']['at'],'#ffe478',4)]:
                    px=x+coord[0]/512*340;py=42+coord[1]/512*340
                    pen.ellipse((px-radius,py-radius,px+radius,py+radius),outline=color,width=2)
                pen.text((x+345,50),e['map'],font=thumb_font,fill='white')
                pen.text((x+345,75),f'floor {m.get("floor")}',font=thumb_font,fill='#b6c6b8')
                pen.text((x+345,100),e['component'][:20],font=thumb_font,fill='#b6c6b8')
                pen.text((x+345,125),'Exit / badge / focus',font=thumb_font,fill='#b6c6b8')
                pen.text((x+345,150),str(e['exit']),font=thumb_font,fill='#ff705b')
                pen.text((x+345,175),str(e['badge']['at']),font=thumb_font,fill='#ffe478')
                pen.text((x+345,200),str(e['arrival']),font=thumb_font,fill='#77c9ff')
            d=ImageDraw.Draw(card)
            d.text((12,390),decision.get('reason','Awaiting independent review')[:135],font=thumb_font,fill='#c2c9bf')
            name=f'{job}--{p["id"]}.png';card.save(output/name);links.append((name,status));cards.append(card)
    pages=[]
    for start in range(0,len(cards),4):
        sheet=Image.new('RGB',(1000,420*len(cards[start:start+4])),(23,37,29))
        for i,card in enumerate(cards[start:start+4]):sheet.paste(card,(0,i*420))
        name=f'contact-{start//4+1:02}.png';sheet.save(output/name);pages.append(name)
    import html
    page='<meta charset="utf-8"><title>Atlas passage review</title><style>body{background:#16251d;color:#eee;font:16px system-ui;max-width:1050px;margin:30px auto}img{width:100%;margin:12px 0}a{color:#d9c08e}</style><h1>Atlas passage review</h1><p>Red: exit; gold: badge; blue: arrival focus. Artwork review, not live traversal.</p>'
    page+=''.join(f'<a href="{html.escape(name)}">{html.escape(name)} — {status}</a><br>' for name,status in links)
    page+=''.join(f'<img src="{name}">' for name in pages)
    (output/'index.html').write_text(page,encoding='utf-8')
    print(f'Rendered {len(cards)} paired review sheets in {output}')
def report():
    manifest,jobs,review,accepted,stats=collect()
    shifts=stats.pop('endpoint_correction_pixels')
    stats['mean_corrected_endpoint_shift']=round(sum(shifts)/len(shifts),2) if shifts else None
    stats['max_corrected_endpoint_shift']=max(shifts) if shifts else None
    stats['accepted_without_review_changes']=stats['accepted']-stats['corrected']
    stats['model_runs']={'annotators':'gpt-6-luna (two independent regional jobs)','checker':'inherited primary model',
        'provider_cost_usd':None,'cost_note':'Subagent tools do not expose billable usage; no dollar savings claim measured.'}
    stats['review_findings']=review.get('findings',[])
    write(DATA/'pilot-report.json',stats)
    summary=f'''# Atlas annotation pilot\n\n{stats['pilot_maps']} maps across Zulkheim, Norvallen and Fauregandi.\n\n| Result | Count |\n|---|---:|\n| Proposed passages | {stats['proposed']} |\n| Accepted after review | {stats['accepted']} |\n| Accepted with corrections | {stats['corrected']} |\n| Rejected | {stats['reject']} |\n| Needs more evidence | {stats['needs_work']} |\n| Pending | {stats['pending']} |\n| Worker unresolved observations | {stats['unresolved']} |\n\nTwo smaller-model regional workers ran in parallel with an independent checker.\nReviews are bound to candidate hashes. Only accepted records are compiled.\nNo in-game traversal verification or measured provider billing is claimed.\n\nThe original Ronfaure seed remains explicitly `legacy_unreviewed`. Pilot records\nare `artwork_reviewed`, a separate status from live traversal verification.\n\nMean exit-anchor shift on corrected accepted records: {stats['mean_corrected_endpoint_shift']}\nreference pixels (512-pixel basis). This is a correction metric, not a global\naccuracy estimate; accepted records and withheld records have different coverage.\n\nDetailed findings: see pilot-report.json, reviews/decisions.json and sheets/index.html.\n'''
    summary+='''\n## What this trial established\n\nThe workers supplied useful connection candidates, but every final accepted record
needed some checker correction. Labels, leader arrows and physical passage mouths
must remain separate concepts in worker prompts and tools. The trial does not
establish that the smaller-model workflow is cheaper overall: checker effort and
provider usage must be measured in a future comparison.

Keep the independent checker for coordinate placement and floor identity. Reuse a
small reviewed example set to improve extraction, reserve a separate holdout set,
and compare accepted-map cost only after wrong-floor and missing-exit checks pass.
Raw worker inventories remain audit observations; only corrected reviewed passages
are used for runtime markers. Shared replacement artwork cannot establish native
floor connectivity; original geometry is required for those cases.
'''
    (DATA/'PILOT_REPORT.md').write_text(summary,encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','check','build','sheets','report'])
    args=parser.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='check':
        *_,stats=collect();print(json.dumps(stats))
    elif args.command=='build':build()
    elif args.command=='sheets':sheets()
    elif args.command=='report':report()
if __name__=='__main__':main()
