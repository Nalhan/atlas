"""Deterministic, cached Horizon wiki/LSB import. Never runs downloaded JavaScript.

fetch requires network; build works offline from pinned snapshots. Runtime Lua
has no network dependency. Existing connectivity/direction is never overwritten.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import argparse
import hashlib
import importlib.util
import json
import math
import re
import urllib.request

ADDON=Path(__file__).resolve().parents[1]
DATA=ADDON/'annotations/imports/horizon'
ASSETS=ADDON/'assets/regions'
WIKI='https://horizonffxi.wiki'
MODULE=WIKI+'/w/load.php?lang=en&modules=ext.FFXIMap&only=scripts&raw=1&skin=timeless'
BASE=WIKI+'/w/extensions/FFXIMap/maps/'
ALIASES={'west':204,'east':108,'fort':110,'outpost':115,'outpost2':116,
    'grotto1':209,'grotto2':210,'tomb1':244,'tomb2':245,'north':22,'south':51,'port':25,
    'chateau':5,'oubliette1':84,'oubliette2':85,'oubliette3':86,'latheine':7,
    'ranguemont':234,'jugner':129,'landing1':226,'landing2':227,'batallia':3,'davoi':107,
    'valkurm':63,'konschtat':6,'selbina':161,'beaucedine':4,'monastic':142,
    'feiyin1':232,'feiyin3':233,'eldieme2':198,'eldieme3':199,'eldieme4':200,
    'ordelle1':235,'ordelle4':236,'ordelle2':237}
ZONE_NAMES={100:'west_ronfaure',101:'east_ronfaure',140:'ghelsba_outpost',141:'fort_ghelsba',
    142:'yughott_grotto',190:'king_ranperres_tomb',230:'southern_san_doria',231:'northern_san_doria',
    232:'port_san_doria',233:'chateau_doraguille',167:'bostaunieux_oubliette',102:'la_theine_plateau',
    166:'ranguemont_pass',104:'jugner_forest',2:'carpenters_landing',105:'batallia_downs',149:'davoi'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regional_builder():
    spec=importlib.util.spec_from_file_location('atlas_regional_art',ADDON/'tools/build_regional_art.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def fetch_one(url,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'AtlasMapPrototype/0.4 (cached map-data import)'})
        with urllib.request.urlopen(req,timeout=60) as response:data=response.read()
        path.write_bytes(data)
    return {'url':url,'path':path.relative_to(ADDON).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size}

def extract_modules(script):
    decoder=json.JSONDecoder();maps={}
    for match in re.finditer(r'"mapdata/json/maps/(\d+)\.json":',script):
        maps[match[1]],_=decoder.raw_decode(script[match.end():])
    if not maps:raise ValueError('No map JSON modules found; wiki module format changed')
    return maps

def fetch():
    rows=[fetch_one(MODULE,DATA/'ffximap.js')]
    # Pin the server snapshot; an existing lock is reused, never silently refreshed.
    lock=DATA/'server-revision.json'
    if not lock.exists():
        req=urllib.request.Request('https://api.github.com/repos/LandSandBoat/server/commits/base',headers={'User-Agent':'AtlasMapPrototype'})
        with urllib.request.urlopen(req,timeout=60) as response:revision=json.load(response)['sha']
        write(lock,{'repository':'https://github.com/LandSandBoat/server','commit':revision})
    revision=read(lock)['commit']
    coordinates=regional_builder().tile_coordinates(read(DATA/'regional-layout-z5.json'))
    requests=[(f'{BASE}tiles/5/{x}/{y}.jpeg',DATA/f'tiles/5/{x}-{y}.jpeg') for x,y in coordinates]
    requests += [(f'https://raw.githubusercontent.com/LandSandBoat/server/{revision}/data/zones/{name}/zone.yaml',DATA/f'server/{name}.yaml') for name in ZONE_NAMES.values()]
    with ThreadPoolExecutor(max_workers=4) as pool:rows+=list(pool.map(lambda args:fetch_one(*args),requests))
    maps=extract_modules((DATA/'ffximap.js').read_text(encoding='utf-8'))
    # Retain only map/connection metadata, excluding unrelated NPC/mob datasets.
    metadata={k:{f:v for f,v in m.items() if f in ('name','filename','bounds','upperBoundX','upperBoundY','connections')}
        for k,m in maps.items()}
    write(DATA/'map-metadata.json',metadata)
    write(DATA/'sources.json',{'fetched_utc':datetime.now(timezone.utc).isoformat(),'files':rows,
        'wiki_module_sha256':sha(DATA/'ffximap.js'),'server_commit':revision,'zoom_level':5})
    print(f'Cached {len(metadata)} map records, {len(coordinates)} level-5 regional tiles and {len(ZONE_NAMES)} server zones')

def rings(value):
    if not isinstance(value,list) or not value:return []
    if all(isinstance(p,list) and len(p)==2 and all(type(n) in (int,float) and math.isfinite(n) for n in p) for p in value):
        return [value] if len(value)>=3 else []
    return [ring for child in value for ring in rings(child)]

def has_holes(value):
    if not isinstance(value,list) or not value:return False
    children=[rings(child) for child in value]
    # A polygon containing several direct rings uses subsequent rings as holes.
    if len(value)>1 and all(len(r)==1 and r[0]==child for child,r in zip(value,children)):return True
    return any(has_holes(child) for child in value)

def map_point(meta,lat_lng):
    lat,lng=lat_lng
    if meta.get('bounds'):
        (xmin,ymin),(xmax,ymax)=meta['bounds']
        return [round((lng-xmin)/(xmax-xmin)*512,3),round((ymax-lat)/(ymax-ymin)*512,3)]
    return [round(lng*2,3),round(512-lat*2,3)]

def point_inside(poly,p):
    x,y=p;inside=False
    for i,(ax,ay) in enumerate(poly):
        bx,by=poly[i-1]
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def parse_server(text):
    result=[];current=None;active=False
    for line in text.splitlines():
        if line=='zonelines:':active=True;continue
        if active and line and not line.startswith((' ','#')):break
        if not active:continue
        match=re.fullmatch(r'  ([a-z0-9]+):\s*',line)
        if match:current={'id':match[1]};result.append(current);continue
        match=re.match(r'    (from|to|at|scale):\s*(.+?)(?:\s+#.*)?$',line)
        if match and current is not None:
            key,value=match.groups();current[key]=json.loads(value) if value.startswith('[') else value
    return [r for r in result if all(k in r for k in ('id','from','to','at'))]

def pipeline():
    spec=importlib.util.spec_from_file_location('atlas_annotations',ADDON/'tools/annotations.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def build():
    p=pipeline();manifest=read(ADDON/'annotations/manifest.json');metadata=read(DATA/'map-metadata.json')
    sources=read(DATA/'sources.json')
    for item in sources['files']:
        if sha(ADDON/item['path'])!=item['sha256']:raise ValueError('Source changed: '+item['path'])
    if metadata!={k:{f:v for f,v in m.items() if f in ('name','filename','bounds','upperBoundX','upperBoundY','connections')}
        for k,m in extract_modules((DATA/'ffximap.js').read_text(encoding='utf-8')).items()}:
        raise ValueError('Extracted metadata differs from the source module')
    dll,base=p.native_table();native={}
    for key,m in manifest['maps'].items():
        if m.get('index') is not None:
            native[key]=p.native_map(dll,base,key,m['zone'],m['floor'],m['index'],m['name'],m['region'])
    lua=p.runtime();catalog=lua.eval("require('src.catalog')")
    catalog_maps={k:p.plain(m) for k,m in catalog['maps'].items()}
    passages=[p.plain(v) for _,v in catalog['passages'].items()]
    wiki_to_native={str(v):k for k,v in ALIASES.items()}
    candidates=[];accepted={};issues=[];all_pulses={}
    for key,identifier in ALIASES.items():
        meta=metadata[str(identifier)];connections=meta.get('connections',{})
        all_pulses[key]=[map_point(meta,pt) for c in connections.values() for pt in c.get('pulse',[])]
        for target_id,c in connections.items():
            target=wiki_to_native.get(target_id)
            polygons=[[map_point(meta,pt) for pt in ring] for ring in rings(c.get('hover',[]))]
            pulses=[map_point(meta,pt) for pt in c.get('pulse',[])]
            existing=[]
            for passage in passages:
                a,b=passage['a'],passage['b']
                if a['map']==key and b['map']==target:existing.append((passage,a,b))
                elif b['map']==key and a['map']==target and not passage.get('one_way'):existing.append((passage,b,a))
            record={'map':key,'wiki_map':identifier,'wiki_target':target_id,'target_map':target,
                'polygons':polygons,'pulses':pulses,'existing_ids':[row[0]['id'] for row in existing]}
            candidates.append(record)
            if has_holes(c.get('hover',[])):
                issues.append({'map':key,'target':target_id,'reason':'Hover polygon has inner rings; hole semantics require review.'});continue
            if not target or not existing:
                issues.append({'map':key,'target':target_id,'reason':'No existing allowed passage / target outside mapped pilot; not auto-published.'});continue
            if len(pulses)!=len(existing):
                issues.append({'map':key,'target':target_id,
                    'reason':f'Entrance-count mismatch: {len(pulses)} wiki pulses, {len(existing)} allowed catalog passages; retained for review.'});continue
            # One named destination can cover several entrances. Publish only a
            # one-to-one pulse assignment with a useful runner-up distance margin.
            assignments=[]
            for passage,endpoint,_ in existing:
                distances=sorted((math.dist([endpoint['x'],endpoint['y']],pt),i) for i,pt in enumerate(pulses))
                if not distances or distances[0][0]>28 or (len(distances)>1 and distances[1][0]-distances[0][0]<8):break
                assignments.append((passage,endpoint,distances[0][1],distances[0][0]))
            if len(assignments)!=len(existing) or len({a[2] for a in assignments})!=len(assignments):
                issues.append({'map':key,'target':target_id,'reason':'Ambiguous or distant pulse assignment; retained for review.'});continue
            for passage,endpoint,pulse_index,distance in assignments:
                shapes=[]
                for polygon in polygons:
                    covered=[i for i,pt in enumerate(pulses) if point_inside(polygon,pt)]
                    if len(assignments)==1 or covered==[pulse_index]:shapes.append(polygon)
                # Shared label shapes must not force a particular entrance.
                if not shapes or any(not (0<=x<=512 and 0<=y<=512) for poly in shapes for x,y in poly):
                    issues.append({'map':key,'id':passage['id'],'reason':'Shared/invalid hover polygon; retained for review.'});continue
                accepted.setdefault(key,{})[passage['id']]={'polygons':shapes,'source':'horizon-wiki',
                    'target_map':target,'wiki_map':identifier,'wiki_target':target_id,'pulse_distance':round(distance,3)}
    server=[];inverse={v:k for k,v in ZONE_NAMES.items()}
    def project(key,position):
        t=native[key]['transform'];factor=abs(t['scale'])/5
        return [round(position[0]*factor-t['offset_x'],3),round(-position[2]*factor-t['offset_y'],3)]
    def choose(zone,position):
        keys=[k for k in ALIASES if native[k]['zone']==zone]
        if len(keys)==1:return keys[0],project(keys[0],position),'single_native_map'
        ranked=[]
        for key in keys:
            pt=project(key,position);d=min((math.dist(pt,pulse) for pulse in all_pulses[key]),default=1e9)
            ranked.append((d,key,pt))
        ranked.sort()
        if ranked and ranked[0][0]<=28 and (len(ranked)==1 or ranked[1][0]-ranked[0][0]>=8):
            return ranked[0][1],ranked[0][2],'wiki_pulse_disambiguation'
        return None,None,'native_floor_ambiguous_or_outside_pilot'
    for zone,name in ZONE_NAMES.items():
        for row in parse_server((DATA/f'server/{name}.yaml').read_text(encoding='utf-8')):
            target_zone=inverse.get(row['to']);a,ap,astatus=choose(zone,row['from']);b,bp,bstatus=choose(target_zone,row['at'])
            server.append({'id':row['id'],'from_zone':zone,'to_zone':target_zone,'target_name':row['to'],
                'from_world_xyz':row['from'],'arrival_world_xyz':row['at'][:3],
                'source_map':a,'exit':ap,'target_map':b,'arrival':bp,
                'source_resolution':astatus,'target_resolution':bstatus,'direction':'a_to_b',
                'source_commit':sources['server_commit'],'publication':'candidate_only'})
    write(DATA/'candidates.json',{'schema_version':1,'wiki':candidates,'server':server,'issues':issues,
        'notes':['Wiki map IDs are not native floor IDs. Aliases are an explicit pilot crosswalk.',
            'Server directions describe the pinned public LSB snapshot, not verified Horizon behavior.',
            'The runtime connectivity, entrance positions and arrival focus are unchanged.']})
    write(DATA/'published-hotspots.json',{'schema_version':1,'areas':accepted,'source_sha256':sources['wiki_module_sha256']})
    (ADDON/'data/wiki_hotspots.lua').write_bytes(('-- Generated by tools/import_horizon.py build; user rectangles override these polygons.\nreturn '+p.lua_value(accepted)+'\n').encode())
    texture_pages=regional_builder().build(p,lua,sources)
    summary={'wiki_maps':len(metadata),'pilot_maps':len(ALIASES),'wiki_connection_groups':len(candidates),
        'published_endpoint_areas':sum(map(len,accepted.values())),'issues':len(issues),'server_directed_candidates':len(server),
        'server_fully_resolved':sum(bool(r['source_map'] and r['target_map']) for r in server),
        'source_sha256':sources['wiki_module_sha256'],'server_commit':sources['server_commit'],
        'manifest_sha256':sha(ADDON/'annotations/manifest.json'),
        'runtime_connectivity_sha256':sha(ADDON/'data/catalog.lua'),
        'runtime_connectivity_changed':sha(ADDON/'data/catalog.lua')!=read(ADDON/'annotations/build.json')['runtime_sha256'],
        'connectivity_scope':'Original reviewed catalog only; the adjacent-region extension is reported in annotations/expansion/build.json.',
        'artwork_zoom_level':5,'regional_texture_pages':texture_pages}
    write(DATA/'report.json',summary)
    (DATA/'REPORT.md').write_text('# Deterministic Horizon import pilot\n\n'+
        '\n'.join(f'- {key}: {value}' for key,value in summary.items())+
        '\n\nPublished areas only bind existing allowed passages. Ambiguous/shared polygons and new connections stay in candidates.json. Server coordinates are candidates; public LSB behavior is not treated as Horizon verification. Manual editor rectangles take priority. Native floor aliases remain explicit.\n',encoding='utf-8')
    print(json.dumps(summary))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['fetch','build']);args=parser.parse_args()
    fetch() if args.command=='fetch' else build()
