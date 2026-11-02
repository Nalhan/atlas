"""Deterministic adjacent-region catalog; no model calls or downloaded code execution."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import importlib.util
import io
import itertools
import json
import math
import re
import urllib.parse
import urllib.request
from PIL import Image,ImageChops,ImageFilter,ImageOps

ADDON=Path(__file__).resolve().parents[1]
DATA=ADDON/'annotations/expansion'
CORE={
    'gustaberg':[11,12,106,107,143,172,173,191,196,234,235,236,237],
    'derfland':[109,110,147,148,197,243,244,245,246],
    'valdeaunia':[5,9,112,161,162],
    'vollbow':[113,128,174,212],
    'qufim':[126,127,157,158,184],
    'aragoneu':[119,120,151,152,200],
    'kolshushu':[4,7,117,118,198,213,249],
    'sarutabaruta':[115,116,145,169,192,194,238,239,240,241],
    'litelor':[121,122,153,154,251],
    'tulia':[130,177,178],
    'kuzotz':[114,125,208,247],
    'elshimo_lowlands':[123,176,250,252],
    'elshimo_uplands':[124,159,160,205],
    'tavnazian_archipelago':[24,25,26,27,28,29,30,32]}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
P=module('atlas_annotations',ADDON/'tools/annotations.py')
W=module('atlas_wiki_import',ADDON/'tools/import_horizon.py')
def norm(s):
    return (''.join(c for c in s.lower() if c.isalnum()).removeprefix('the')
        .replace('crawlers','crawler').replace('santuary','sanctuary').replace('outterhorutoto','outerhorutotoruins'))
def wiki_zone(name):
    return norm('Riverne - Site #A01') if name.startswith('Riverne Site #A01 - Map 1') else norm(name.split(':')[0])
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resources():
    lua=P.runtime();zones=lua.execute('return dofile(...)',str(ADDON.parent/'boussole/data/zones.lua'))
    if isinstance(zones,tuple):zones=zones[0]
    floors=lua.execute('return dofile(...)',str(ADDON.parent/'boussole/data/zonesFloors.lua'))
    return lua,{int(k):P.plain(v) for k,v in zones.items()},{int(k):{int(f):int(i) for f,i in v.items()} for k,v in floors.items()}

def fetch():
    _,zones,_=resources();meta=read(W.DATA/'map-metadata.json');revision=read(W.DATA/'server-revision.json')['commit']
    index=DATA/'server-paths.json'
    if not index.exists():
        url=f'https://api.github.com/repos/LandSandBoat/server/git/trees/{revision}?recursive=1'
        req=urllib.request.Request(url,headers={'User-Agent':'AtlasMapPrototype/0.5'})
        with urllib.request.urlopen(req,timeout=60) as r:tree=json.load(r)
        paths=[row['path'] for row in tree['tree'] if re.fullmatch(r'data/zones/[^/]+/zone.yaml',row['path'])]
        write(index,{'commit':revision,'paths':paths})
    paths=read(index)
    if paths['commit']!=revision:raise ValueError('Server directory index revision mismatch')
    by_name={norm(Path(path).parent.name):path for path in paths['paths']}
    ids=sorted(set(itertools.chain.from_iterable(CORE.values())))
    baseline=read(ADDON/'annotations/manifest.json')['maps']
    server_ids=sorted(set(ids+[m['zone'] for m in baseline.values()]))
    requests=[];zone_files={};wiki_ids={}
    for zone in server_ids:
        path=by_name.get(norm(zones[zone]['en']))
        if path:
            zone_files[str(zone)]=path
            requests.append((f'https://raw.githubusercontent.com/LandSandBoat/server/{revision}/{path}',DATA/f'server/{zone}.yaml'))
    for zone in ids:
        matches=[k for k,v in meta.items() if isinstance(v,dict) and wiki_zone(v.get('name',''))==norm(zones[zone]['en'])]
        wiki_ids[str(zone)]=matches
        for key in matches:
            filename=meta[key].get('filename')
            if filename:requests.append((W.BASE+'zones/'+urllib.parse.quote(filename),DATA/f'wiki-images/{key}-{filename}'))
    def get(args):
        url,path=args;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AtlasMapPrototype/0.5 (cached deterministic region import)'}),timeout=60) as r:path.write_bytes(r.read())
        return {'url':url,'path':path.relative_to(ADDON).as_posix(),'sha256':sha(path)}
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(get,requests))
    write(DATA/'sources.json',{'server_commit':revision,'wiki_module_sha256':sha(W.DATA/'ffximap.js'),
        'zone_files':zone_files,'wiki_ids':wiki_ids,'files':rows,'regions':CORE})
    print(f'Cached {len(rows)} source files for {len(ids)} zones in {len(CORE)} regions',flush=True)

def ink(image):
    gray=ImageOps.grayscale(image.convert('RGB').resize((512,512),Image.Resampling.LANCZOS))
    contrast=ImageChops.subtract(gray.filter(ImageFilter.MaxFilter(7)),gray)
    return contrast.point(lambda n:255 if n>=18 else 0).crop((70,95,445,430)).filter(ImageFilter.MaxFilter(3))
def similarity(a,b):
    count_a=a.histogram()[255];count_b=b.histogram()[255]
    return 2*ImageChops.multiply(a,b).histogram()[255]/max(1,count_a+count_b)
def original(definition,wrap):
    _,_,rel=P.artwork(definition);path=P.ROOT/'SquareEnix/FINAL FANTASY XI'/rel
    raw=path.read_bytes();identity=f'm_{definition["zone"]:03}_{definition["floor"]:02}'.encode()
    alt=b'm_251_00' if (definition['zone'],definition['floor'])==(251,1) else identity
    if identity not in raw[49:65] and alt not in raw[49:65]:raise ValueError('Native DAT identity mismatch')
    image,_,_=wrap(raw)
    if not image:raise ValueError('Native DAT could not be decoded')
    return Image.open(io.BytesIO(image)).convert('RGB'),sha(path)

def connections(maps,aliases,baseline,source,meta,exclude_pairs=()):
    by_key={m['key']:m for m in maps};by_zone={}
    for key in set(aliases.values()):by_zone.setdefault(by_key[key]['zone'],[]).append(key)
    wiki_for={key:wid for wid,key in aliases.items()}
    server_names={norm(Path(path).parent.name):int(zone) for zone,path in source['zone_files'].items()}
    raw_rows=[];held=[];direct=[]
    for zone in source['zone_files']:
        for row in W.parse_server((DATA/f'server/{zone}.yaml').read_text(encoding='utf-8')):
            raw_rows.append(dict(row,zone=int(zone),target_zone=server_names.get(norm(row['to']))))
    def projected(key,position):
        t=by_key[key]['transform'];f=abs(t['scale'])/5
        return [round(position[0]*f-t['offset_x'],3),round(-position[2]*f-t['offset_y'],3)]
    def pulses(key,other_zone):
        info=meta[wiki_for[key]];result=[]
        for target,record in info.get('connections',{}).items():
            target_key=aliases.get(target)
            if target_key and by_key[target_key]['zone']==other_zone:
                result += [W.map_point(info,point) for point in record.get('pulse',[])]
        return result
    def resolve(zone,position,other_zone,incoming=False):
        ranked=[]
        for key in by_zone.get(zone,[]):
            point=projected(key,position)
            if any(n<0 or n>512 for n in point):continue
            points=pulses(key,other_zone)
            if not points and not (incoming and len(by_zone[zone])==1):continue
            distance=min((math.dist(point,p) for p in points),default=0)
            ranked.append((distance,key,point))
        ranked.sort()
        if ranked and ranked[0][0]<=32 and (len(ranked)==1 or ranked[1][0]-ranked[0][0]>=8):return ranked[0][1],ranked[0][2]
        return None,None
    def already(a,b,pa,pb):
        for old in baseline:
            oa,ob=old['a'],old['b']
            za,zb=by_key[oa['map']]['zone'],by_key[ob['map']]['zone']
            if old.get('one_way') and (by_key[a]['zone'],by_key[b]['zone'])==(zb,za):return 'existing_one_way_protected'
            for x,y in [(oa,ob)]+([] if old.get('one_way') else [(ob,oa)]):
                if x['map']==a and y['map']==b and math.dist([x['x'],x['y']],pa)<28 and math.dist([y['x'],y['y']],pb)<40:return 'covered'
        return None
    for row in raw_rows:
        if frozenset((row['zone'],row['target_zone'])) in exclude_pairs:
            held.append({'id':row['id'],'reason':'Transport route; kept outside walking connections'});continue
        a,pa=resolve(row['zone'],row['from'],row['target_zone'])
        b,pb=resolve(row['target_zone'],row['at'],row['zone'],True)
        if not a or not b:
            held.append({'id':row['id'],'source':'server','reason':'Unknown target or ambiguous native floor / wiki entrance'});continue
        reason=already(a,b,pa,pb)
        if reason:
            if reason!='covered':held.append({'id':row['id'],'reason':reason})
            continue
        direct.append({'id':row['id'],'a':a,'b':b,'exit':pa,'arrival':pb,'source':'server_wiki_correlated'})
    # Wiki-only stairs and city links: match reciprocal world-space endpoints
    # inside one zone; across zones require exactly one entrance at each end.
    def world_xy(key,p):
        t=by_key[key]['transform'];f=abs(t['scale'])/5
        return [(p[0]+t['offset_x'])/f,-(p[1]+t['offset_y'])/f]
    for wid,a in sorted(aliases.items()):
        info=meta[wid]
        for target,record in info.get('connections',{}).items():
            b=aliases.get(target)
            if not b or a==b:continue
            if frozenset((by_key[a]['zone'],by_key[b]['zone'])) in exclude_pairs:
                held.append({'id':f'wiki-{wid}-{target}','reason':'Transport route; kept outside walking connections'});continue
            def city(zone):
                if 230<=zone<=233:return 'sandoria'
                if 234<=zone<=237:return 'bastok'
                if 238<=zone<=241:return 'windurst'
                if 243<=zone<=246:return 'jeuno'
                if zone in (248,249,250):return f'hub_{zone}'
            ca,cb=city(by_key[a]['zone']),city(by_key[b]['zone'])
            if ca and cb and ca!=cb:
                held.append({'id':f'wiki-{wid}-{target}','reason':'Remote-city transport; excluded from walking connections'});continue
            reverse=meta[target].get('connections',{}).get(wid)
            if not reverse:continue
            ap=[W.map_point(info,p) for p in record.get('pulse',[])]
            bp=[W.map_point(meta[target],p) for p in reverse.get('pulse',[])]
            for i,point in enumerate(ap):
                if by_key[a]['zone']==by_key[b]['zone']:
                    choices=sorted((math.dist(world_xy(a,point),world_xy(b,p)),j) for j,p in enumerate(bp))
                    if not choices or choices[0][0]>60 or (len(choices)>1 and choices[1][0]-choices[0][0]<16):continue
                    j=choices[0][1]
                    back=sorted((math.dist(world_xy(b,bp[j]),world_xy(a,p)),k) for k,p in enumerate(ap))
                    if back[0][1]!=i or (len(back)>1 and back[1][0]-back[0][0]<16):continue
                elif len(ap)==len(bp)==1:j=0
                else:continue
                if already(a,b,point,bp[j]):continue
                if any(r['a']==a and r['b']==b and math.dist(r['exit'],point)<=24
                    and math.dist(r['arrival'],bp[j])<=24 for r in direct):continue
                direct.append({'id':f'wiki-{wid}-{target}-{i}','a':a,'b':b,'exit':point,'arrival':bp[j],'source':'wiki_reciprocal'})
    passages=[];used=set()
    def endpoint(key,point,arrival):
        return {'map':key,'x':point[0],'y':point[1],'arrival_x':arrival[0],'arrival_y':arrival[1],
            'badge_x':point[0],'badge_y':point[1],'printed':False,'component':'main'}
    for i,row in enumerate(direct):
        if i in used:continue
        reverses=sorted((math.dist(row['exit'],r['arrival'])+math.dist(row['arrival'],r['exit']),j)
            for j,r in enumerate(direct) if j not in used and j!=i and r['a']==row['b'] and r['b']==row['a']
            and math.dist(row['exit'],r['arrival'])<=24 and math.dist(row['arrival'],r['exit'])<=24)
        if not reverses or (len(reverses)>1 and reverses[1][0]-reverses[0][0]<8):
            held.append({'id':row['id'],'reason':'Reciprocal passage pairing ambiguous'});continue
        j=reverses[0][1];other=direct[j];used.update((i,j))
        a=endpoint(row['a'],row['exit'],other['arrival']);b=endpoint(row['b'],other['exit'],row['arrival'])
        duplicate=False
        for old in passages:
            for x,y in [(old['a'],old['b']),(old['b'],old['a'])]:
                if x['map']==a['map'] and y['map']==b['map']:
                    near_exit=math.dist([x['x'],x['y']],row['exit'])
                    near_arrival=math.dist([y['x'],y['y']],other['exit'])
                    if near_exit<25 or (old['source_method']!=row['source'] and near_exit<=32 and near_arrival<=32):duplicate=True
        if duplicate:continue
        passages.append({'id':'auto-'+min(row['id'],other['id']),'a':a,'b':b,'note':'',
            'status':'source_correlated','source_method':row['source'],'source_ids':[row['id'],other['id']]})
    hotspots={}
    for passage in passages:
        for side,target in [('a','b'),('b','a')]:
            e,t=passage[side],passage[target];wid=wiki_for[e['map']];tid=wiki_for[t['map']]
            record=meta[wid].get('connections',{}).get(tid,{})
            polygons=[[W.map_point(meta[wid],p) for p in ring] for ring in W.rings(record.get('hover',[]))]
            points=[W.map_point(meta[wid],p) for p in record.get('pulse',[])]
            shapes=polygons if len(points)==1 else [poly for poly in polygons if W.point_inside(poly,[e['x'],e['y']])]
            if shapes and not W.has_holes(record.get('hover',[])) and all(0<=v<=512 for poly in shapes for p in poly for v in p):
                hotspots.setdefault(e['map'],{})[passage['id']]={'target_map':t['map'],'polygons':shapes,'source':'horizon-wiki'}
    return passages,hotspots,held,direct

def build():
    source=read(DATA/'sources.json');meta=read(W.DATA/'map-metadata.json')
    if '197' in meta.get('282',{}).get('connections',{}) and '201' not in meta['282']['connections']:
        meta['282']=dict(meta['282'],connections=dict(meta['282']['connections']))
        meta['282']['connections']['201']=meta['282']['connections'].pop('197')
    if sha(W.DATA/'ffximap.js')!=source['wiki_module_sha256']:raise ValueError('Wiki source changed')
    for row in source['files']:
        if sha(ADDON/row['path'])!=row['sha256']:raise ValueError('Source changed: '+row['path'])
    lua,zones,floors=resources();dll,base=P.native_table();raw=P.runtime(True);wrap=raw.eval(b"require('src.dat_image').wrap")
    baseline=P.plain(lua.eval("require('data.catalog')"));maps=baseline['maps'];base_passages=baseline['passages']
    existing={(m['zone'],m.get('floor')):m for m in maps};new_maps=[];aliases={str(v):k for k,v in W.ALIASES.items()}
    aliases.update({'63':'valkurm','6':'konschtat','161':'selbina','4':'beaucedine','142':'monastic',
        '232':'feiyin1','233':'feiyin3','198':'eldieme2','199':'eldieme3','200':'eldieme4',
        '235':'ordelle1','236':'ordelle4','237':'ordelle2'})
    matching=[];held=[]
    for region,zone_ids in CORE.items():
        for zone in zone_ids:
            candidates=[]
            for floor,index in floors.get(zone,{}).items():
                # High-index later-client map variants are outside this era pilot.
                if index>=300:continue
                try:
                    d=P.native_map(dll,base,'candidate',zone,int(floor),int(index),zones[zone]['en'],region)
                    image,digest=original(d,wrap);candidates.append((d,ink(image),digest))
                except (ValueError,KeyError,FileNotFoundError):continue
            ids=source['wiki_ids'][str(zone)];scores={};wiki_masks={}
            for key in ids:
                filename=meta[key].get('filename');path=DATA/f'wiki-images/{key}-{filename}'
                wiki_masks[key]=ink(Image.open(path))
            # Shared parchment/grid pixels do not identify a floor. Compare the
            # discriminating ink after removing pixels common to all its floors.
            if len(candidates)>1 and len(ids)>1:
                common_native=candidates[0][1]
                for _,mask,_ in candidates[1:]:common_native=ImageChops.darker(common_native,mask)
                common_wiki=wiki_masks[ids[0]]
                for key in ids[1:]:common_wiki=ImageChops.darker(common_wiki,wiki_masks[key])
                candidates=[(d,ImageChops.subtract(mask,common_native),digest) for d,mask,digest in candidates]
                wiki_masks={key:ImageChops.subtract(mask,common_wiki) for key,mask in wiki_masks.items()}
            for key in ids:scores[key]=[similarity(wiki_masks[key],m[1]) for m in candidates]
            for key in ids:
                ranked=sorted(((value,i) for i,value in enumerate(scores[key])),reverse=True)
                if not ranked:held.append({'wiki_map':key,'reason':'No verified era-native map entry'});continue
                score,index=ranked[0];reverse=sorted((scores[k][index],k) for k in ids)[::-1]
                unique=len(ids)==1 and len(candidates)==1
                margin=score-ranked[1][0] if len(ranked)>1 else 1
                reverse_margin=reverse[0][0]-reverse[1][0] if len(reverse)>1 else 1
                ok=unique or (score>=.20 and margin>=.035 and reverse[0][1]==key and reverse_margin>=.035)
                result={'wiki_map':key,'zone':zone,'score':round(score,4),'floor_margin':round(margin,4),
                    'image_margin':round(reverse_margin,4),'accepted':ok,
                    'candidate_scores':[{'floor':d['floor'],'score':round(scores[key][i],4)} for i,(d,_,_) in enumerate(candidates)]}
                matching.append(result)
                if not ok:held.append(dict(result,reason='Ambiguous native-floor artwork match'));continue
                definition,_,digest=candidates[index]
                if (zone,definition['floor']) in existing:
                    aliases[key]=existing[zone,definition['floor']]['key'];continue
                name=re.sub(r'[^a-z0-9]+','_',zones[zone]['en'].lower()).strip('_')
                name=name if len(ids)==1 else name+'_f'+str(definition['floor'])
                definition.update(key=name,name=zones[zone]['en']+((' / '+meta[key]['name'].split(':',1)[1].strip()) if ':' in meta[key]['name'] else ''),
                    tab=meta[key]['name'] if 238<=zone<=241 else (meta[key]['name'].split(':')[-1].strip() if ':' in meta[key]['name'] else zones[zone]['en']),
                    artwork_sha256=digest,wiki_map=int(key),status='deterministic_import')
                new_maps.append(definition);existing[zone,definition['floor']]=definition;aliases[key]=name
    write(DATA/'floor-matches.json',{'matches':matching,'held':held,'aliases':aliases})
    new_maps.sort(key=lambda m:(m['region'],m['zone'],m['floor']))
    for m in maps:
        if m.get('index') is not None:
            m['transform']=P.native_map(dll,base,m['key'],m['zone'],m['floor'],m['index'],m['name'],m['region'])['transform']
    all_maps=maps+new_maps
    passages,hotspots,connection_held,directed=connections(all_maps,aliases,base_passages,source,meta)
    write(DATA/'draft-maps.json',{'maps':new_maps,'aliases':aliases})
    write(DATA/'connection-review.json',{'held':connection_held,'directed_candidates':directed,'published':passages})
    out={'maps':[{k:v for k,v in m.items() if k!='transform'} for m in new_maps],'passages':passages}
    (ADDON/'data/expansion.lua').write_bytes(('-- Generated by tools/expand_regions.py build; source-correlated, not traversal-verified.\nreturn '+P.lua_value(out)+'\n').encode())
    (ADDON/'data/expanded_hotspots.lua').write_bytes(('-- Generated additional wiki polygon hits; manual rectangles take priority.\nreturn '+P.lua_value(hotspots)+'\n').encode())
    boards=make_boards(all_maps,base_passages+passages)
    (ADDON/'data/expanded_regions.lua').write_bytes(('-- Generated adjacent-region fallback boards.\nreturn '+P.lua_value(boards)+'\n').encode())
    summary={'new_regions':list(CORE),'new_maps':len(new_maps),'new_passages':len(passages),
        'held_native_maps':len(held),'held_connections':len(connection_held),'published_polygon_endpoints':sum(len(v) for v in hotspots.values()),
        'base_catalog_sha256':sha(ADDON/'data/catalog.lua'),'generated_sha256':sha(ADDON/'data/expansion.lua'),
        'sources_sha256':sha(DATA/'sources.json'),'traversal_verified':False}
    write(DATA/'build.json',summary)
    (DATA/'REPORT.md').write_text('# Deterministic adjacent-region expansion\n\n'+
        '\n'.join(f'- {k}: {v}' for k,v in summary.items())+
        '\n\nFloor aliases require verified native DAT identities; multiple-floor zones also require mutual-best discriminating artwork matches. Shared parchment/grid pixels are removed before matching. Connections require uniquely paired reciprocal endpoints, using server coordinates correlated with wiki entrances or explicit reciprocal wiki links. Unpaired server candidates do not suppress wiki fallback links; nearby cross-source duplicates are removed. Existing one-way restrictions are protected and remote-city transport links are excluded. Deferred matches are recorded in floor-matches.json and connection-review.json. No provider/model calls are used. These connections have not been traversal-verified on Horizon.\n',encoding='utf-8')
    print(json.dumps(summary))

def make_boards(maps,passages):
    by_key={m['key']:m for m in maps};anchors=read(DATA/'world-anchors.json');layout=read(W.DATA/'regional-layout-z5.json');boards={}
    by_zone={}
    for m in maps:by_zone.setdefault(m['zone'],[]).append(m)
    def in_crop(zone,crop):
        first=by_zone[zone][0]
        box=anchors.get(str(zone)) or layout['anchors'].get(first['key'])
        return bool(box and crop[0]<=box[0]<box[2]<=crop[2] and crop[1]<=box[1]<box[3]<=crop[3])
    for region in CORE:
        crop=layout['regions'][region]
        core={m['zone'] for m in maps if m['region']==region};zones=set(core)
        for p in passages:
            a,b=by_key[p['a']['map']]['zone'],by_key[p['b']['map']]['zone']
            if a in core and (b in core or in_crop(b,crop)):zones.add(b)
            if b in core and (a in core or in_crop(a,crop)):zones.add(a)
        groups={}
        for m in maps:
            if m['zone'] not in zones:continue
            group='bastok' if 234<=m['zone']<=237 else 'windurst' if 238<=m['zone']<=241 else 'jeuno' if 243<=m['zone']<=246 else str(m['zone'])
            groups.setdefault(group,[]).append(m)
        nodes={};by_map={};order=[]
        for i,(group,definitions) in enumerate(sorted(groups.items())):
            key='hub_'+group;angle=i*2*math.pi/max(1,len(groups));first=definitions[0]
            node={'key':key,'title':group.title() if group in ('bastok','windurst','jeuno') else first['name'].split(' / ')[0],
                'maps':[m['key'] for m in definitions],'x':round(750+450*math.cos(angle)),'y':round(560+380*math.sin(angle)),
                'w':240,'h':170,'crop':[.18,.18,.84,.84],'external':first['zone'] not in core,
                'supplementary':first['zone'] in (12,27,28,32,127,128,148,152,157,158,162,169,172,177,184,213,251)}
            if str(first['zone']) in anchors:node['world_anchor']=anchors[str(first['zone'])]
            nodes[key]=node;order.append(key)
            for m in definitions:by_map[m['key']]=key
        boards[region]={'id':region,'title':region.upper(),'width':1500,'height':1120,'nodes':nodes,'order':order,'by_map':by_map}
    return boards

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['fetch','build']);args=parser.parse_args()
    fetch() if args.command=='fetch' else build()
