"""Besieged overview and native Aht Urhgan maps, from cached deterministic sources."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import shutil
from PIL import Image

ADDON=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
E=module('atlas_aht_sources',ADDON/'tools/expand_regions.py')
P=E.P;W=E.W
DATA=ADDON/'annotations/aht-urhgan'
CORE={
    'western_aradjiah':[46,47,58,59],
    'west_aht_urhgan':[48,50,52,71],
    'mamool_ja_savagelands':[51,65,66,67,68,69],
    'halvung_territory':[61,62,63,64],
    'arrapago_islands':[53,54,55,56,57,60,78,79],
    'ruins_of_alzadaal':[72,73,74,75,76,77]}
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):P.write(Path(path),value)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fetch():
    DATA.mkdir(parents=True,exist_ok=True)
    index=DATA/'server-paths.json'
    if not index.exists():shutil.copyfile(ADDON/'annotations/expansion/server-paths.json',index)
    E.DATA=DATA;E.CORE=CORE;E.fetch()

def build():
    source=read(DATA/'sources.json');meta=read(W.DATA/'map-metadata.json')
    if sha(W.DATA/'ffximap.js')!=source['wiki_module_sha256']:raise ValueError('Wiki module changed')
    for row in source['files']:
        if sha(ADDON/row['path'])!=row['sha256']:raise ValueError('Source changed: '+row['path'])
    lua,zones,floors=E.resources();dll,base=P.native_table();binary=P.runtime(True);wrap=binary.eval(b"require('src.dat_image').wrap")
    baseline=P.plain(lua.eval("require('data.catalog')"));extension=P.plain(lua.eval("require('data.expansion')"))
    old_maps=baseline['maps']+extension['maps'];old_passages=baseline['passages']+extension['passages']
    aliases=read(ADDON/'annotations/expansion/floor-matches.json')['aliases'].copy()
    maps=[];matching=[];held=[];mapless=[];references={}
    for region,ids in CORE.items():
        for zone in ids:
            candidates=[]
            for floor,index in sorted(floors.get(zone,{}).items()):
                # The original Treasures map block ends at index 431. Later
                # event/duplicate variants are not presumed equivalent floors.
                if not 294<=index<=431:continue
                try:
                    d=P.native_map(dll,base,'candidate',zone,floor,index,zones[zone]['en'],region)
                    image,digest=E.original(d,wrap);d['pixel_sha256']=hashlib.sha256(image.tobytes()).hexdigest()
                    candidates.append((d,E.ink(image),digest))
                except (ValueError,KeyError,FileNotFoundError) as error:
                    held.append({'zone':zone,'floor':floor,'reason':str(error)})
            ids=source['wiki_ids'][str(zone)];wiki_masks={}
            for key in ids:
                filename=meta[key].get('filename')
                if filename:wiki_masks[key]=E.ink(Image.open(DATA/f'wiki-images/{key}-{filename}'))
            ids=list(wiki_masks)
            # Publish validated native maps independently of the wiki crosswalk.
            # An ambiguous wiki alias holds exits, not the installed map itself.
            for d,_,digest in candidates:
                key=E.re.sub(r'[^a-z0-9]+','_',zones[zone]['en'].lower()).strip('_')
                if len(candidates)>1:key+='_f'+str(d['floor'])
                d.update(key=key,name=zones[zone]['en']+((' / Map '+str(d['floor'])) if len(candidates)>1 else ''),
                    tab=('Map '+str(d['floor'])) if len(candidates)>1 else zones[zone]['en'],
                    artwork_sha256=digest,status='native_verified',overview='besieged')
                maps.append(d)
            if not candidates:
                key=E.re.sub(r'[^a-z0-9]+','_',zones[zone]['en'].lower()).strip('_')
                if wiki_masks:
                    for ordinal,wid in enumerate(wiki_masks,1):
                        name=key if len(wiki_masks)==1 else key+'_reference_'+str(ordinal)
                        image=Image.open(DATA/f"wiki-images/{wid}-{meta[wid]['filename']}").convert('RGB').resize((512,512),Image.Resampling.LANCZOS)
                        asset=ADDON/f'assets/references/aht-{wid}.png';asset.parent.mkdir(parents=True,exist_ok=True);image.save(asset)
                        definition={'key':name,'zone':zone,'floor':-ordinal,'name':meta[wid]['name'].replace(':',' /',1),
                            'tab':meta[wid]['name'].split(':')[-1].strip(),'region':region,'status':'reference_only',
                            'reference_only':True,'asset':asset.relative_to(ADDON).as_posix(),'overview':'besieged','wiki_map':int(wid)}
                        maps.append(definition);references[wid]=definition
                else:
                    maps.append({'key':key,'zone':zone,'name':zones[zone]['en'],'tab':zones[zone]['en'],
                        'region':region,'status':'uncharted','overview':'besieged'})
                    mapless.append({'zone':zone,'name':zones[zone]['en'],'reason':'No standard native map or cached reference artwork.'})
            compare=[m for _,m,_ in candidates]
            if len(candidates)>1 and len(ids)>1:
                common=compare[0]
                for mask in compare[1:]:common=E.ImageChops.darker(common,mask)
                common_wiki=wiki_masks[ids[0]]
                for key in ids[1:]:common_wiki=E.ImageChops.darker(common_wiki,wiki_masks[key])
                compare=[E.ImageChops.subtract(mask,common) for mask in compare]
                wiki_masks={key:E.ImageChops.subtract(mask,common_wiki) for key,mask in wiki_masks.items()}
            scores={key:[E.similarity(mask,native) for native in compare] for key,mask in wiki_masks.items()}
            for key in ids:
                ranked=sorted((score,i) for i,score in enumerate(scores[key]))[::-1]
                if not ranked:continue
                score,index=ranked[0];reverse=sorted((scores[k][index],k) for k in ids)[::-1]
                margin=score-ranked[1][0] if len(ranked)>1 else 1
                back_margin=reverse[0][0]-reverse[1][0] if len(reverse)>1 else 1
                accepted=(len(ids)==len(candidates)==1) or (score>=.20 and margin>=.035 and reverse[0][1]==key and back_margin>=.035)
                geometry=[]
                if not accepted and len(ids)==1 and len(candidates)>1:
                    rows=W.parse_server((DATA/f'server/{zone}.yaml').read_text()) if (DATA/f'server/{zone}.yaml').exists() else []
                    for i,(native,_,_) in enumerate(candidates):
                        distances=[];t=native['transform'];f=abs(t['scale'])/5
                        for row in rows:
                            pulse=[]
                            for target,connection in meta[key].get('connections',{}).items():
                                if target in meta and E.wiki_zone(meta[target].get('name',''))==E.norm(row['to']):
                                    pulse.extend(W.map_point(meta[key],pt) for pt in connection.get('pulse',[]))
                            if pulse:
                                point=[row['from'][0]*f-t['offset_x'],-row['from'][2]*f-t['offset_y']]
                                distances.append(min(E.math.dist(point,pt) for pt in pulse))
                        geometry.append({'index':i,'matches':sum(d<=24 for d in distances),
                            'mean_error':sum(distances)/len(distances) if distances else 1e9})
                    geometry.sort(key=lambda r:(-r['matches'],r['mean_error']))
                    duplicate_pixels=len({d['pixel_sha256'] for d,_,_ in candidates})==1
                    sufficient=geometry[0]['matches']>=2 or (duplicate_pixels and geometry[0]['matches']>=1
                        and geometry[1]['mean_error']-geometry[0]['mean_error']>=32)
                    if sufficient and geometry[0]['mean_error']<8 and (
                        geometry[0]['matches']>geometry[1]['matches'] or geometry[1]['mean_error']-geometry[0]['mean_error']>=8):
                        index=geometry[0]['index'];accepted=True
                record={'wiki_map':key,'zone':zone,'score':round(score,4),'floor_margin':round(margin,4),
                    'image_margin':round(back_margin,4),'accepted':accepted,'native_map':candidates[index][0]['key']}
                if geometry:record['server_geometry']=geometry
                matching.append(record)
                if accepted:
                    aliases[key]=candidates[index][0]['key'];candidates[index][0]['wiki_map']=int(key)
                    candidates[index][0]['tab']=meta[key]['name'].split(':')[-1].strip()
                    candidates[index][0]['name']=meta[key]['name'].replace(':',' /',1)
                else:held.append(dict(record,reason='Ambiguous wiki/native-floor artwork correlation; native map remains available.'))
    for d in old_maps:
        if d.get('index') is not None:
            d['transform']=P.native_map(dll,base,d['key'],d['zone'],d['floor'],d['index'],d['name'],d['region'])['transform']
    E.DATA=DATA
    passages,hotspots,connection_held,directed=E.connections(old_maps+maps,aliases,old_passages,source,meta,
        exclude_pairs={frozenset((50,249)),frozenset((50,53))})
    for passage in passages:
        endpoints=[next(d for d in maps+old_maps if d['key']==passage[s]['map']) for s in ('a','b')]
        if any(zones[d['zone']].get('is_layered') for d in endpoints):passage['note']='Instance entrance; access requirements apply.'
        if {d['zone'] for d in endpoints} in ({50,51},{50,52}):
            passage['kind']='runic_portal';passage['note']='Runic portal; staging-point access required.'
        passage['id']='aht-'+passage['id']
    # Keep hotspot IDs aligned after namespacing passages.
    hotspots={key:{'aht-'+pid:record for pid,record in values.items()} for key,values in hotspots.items()}
    for wid,definition in references.items():
        for target,connection in meta[wid].get('connections',{}).items():
            destination=aliases.get(target);reverse=meta.get(target,{}).get('connections',{}).get(wid)
            if not destination or not reverse:continue
            ap=connection.get('pulse',[]);bp=reverse.get('pulse',[])
            if len(ap)!=1 or len(bp)!=1:continue
            a=W.map_point(meta[wid],ap[0]);b=W.map_point(meta[target],bp[0]);pid=f'aht-reference-{wid}-{target}'
            def endpoint(key,point):return {'map':key,'x':point[0],'y':point[1],'arrival_x':point[0],'arrival_y':point[1]}
            passages.append({'id':pid,'a':endpoint(definition['key'],a),'b':endpoint(destination,b),
                'status':'source_correlated','source_method':'wiki_reference_reciprocal',
                'note':'Reference map; precise player positions unavailable here.'})
    result={'maps':[{k:v for k,v in d.items() if k!='transform'} for d in maps],'passages':passages}
    (ADDON/'data/aht_urhgan.lua').write_bytes(('-- Generated native Treasures maps and source-correlated links.\nreturn '+P.lua_value(result)+'\n').encode())
    (ADDON/'data/aht_hotspots.lua').write_bytes(('-- Generated Aht Urhgan click polygons; manual rectangles override.\nreturn '+P.lua_value(hotspots)+'\n').encode())
    layout=read(DATA/'layout.json');boards={}
    for region,zone_ids in CORE.items():
        nodes={};order=[];by_map={}
        for i,zone in enumerate(zone_ids):
            definitions=[d for d in maps if d['zone']==zone];key='zone_'+str(zone)
            node={'key':key,'title':zones[zone]['en'],'maps':[d['key'] for d in definitions],
                'x':250+(i%4)*300,'y':160+(i//4)*240,'w':240,'h':170,'crop':[.1,.1,.9,.9]}
            nodes[key]=node;order.append(key)
            for d in definitions:by_map[d['key']]=key
        boards[region]={'id':region,'title':layout['regions'][region]['title'],'width':1500,'height':1120,
            'nodes':nodes,'order':order,'by_map':by_map}
    (ADDON/'data/aht_regions.lua').write_bytes(('-- Generated Aht Urhgan map group references.\nreturn '+P.lua_value(boards)+'\n').encode())
    write(DATA/'floor-matches.json',{'matches':matching,'held':held,'aliases':aliases,'uncharted':mapless})
    write(DATA/'connection-review.json',{'published':passages,'held':connection_held,'directed_candidates':directed})
    write(DATA/'maps.json',{'maps':maps})
    reference_assets={d['asset']:sha(ADDON/d['asset']) for d in maps if d.get('reference_only')}
    write(ADDON/'assets/references/SOURCES.json',{'source':'https://horizonffxi.wiki/Interactive_Map',
        'assets':reference_assets,'attribution':'HorizonXI Wiki / FFXI Atlas / Square Enix',
        'policy':'Reference artwork normalized to 512 pixels. Native floors and precise entity positions are not inferred.'})
    report={'regions':list(CORE),'native_maps':sum(d.get('index') is not None for d in maps),'uncharted_zones':len(mapless),
        'reference_maps':len(references),'passages':len(passages),'held_aliases':len(held),'held_connections':len(connection_held),
        'sources_sha256':sha(DATA/'sources.json'),'output_sha256':sha(ADDON/'data/aht_urhgan.lua'),'traversal_verified':False}
    write(DATA/'build.json',report);print(json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['fetch','build']);args=parser.parse_args()
    fetch() if args.command=='fetch' else build()
