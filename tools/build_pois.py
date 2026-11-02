"""Offline transport POIs from pinned wiki pulses and validated native transforms."""
from pathlib import Path
import hashlib
import importlib.util
import json

ADDON=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
P=module('poi_annotations',ADDON/'tools/annotations.py')
W=module('poi_wiki',ADDON/'tools/import_horizon.py')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boarding_pulses(info,target):
    record=info.get('connections',{}).get(target)
    if record:return record.get('pulse',[])
    groups=[r for r in info.get('connections',{}).values() if str(target) in {str(v) for v in r.get('links',[])}]
    return groups[0].get('pulse',[]) if len(groups)==1 else []

def build(corrections_path=None,write_outputs=True):
    seed_path=ADDON/'annotations/poi/transport.json';seed=P.read(seed_path)
    lock=P.read(W.DATA/'sources.json');wiki=W.DATA/'ffximap.js'
    if sha(wiki)!=lock['wiki_module_sha256']:raise ValueError('Wiki module fingerprint changed')
    metadata=W.extract_modules(wiki.read_text(encoding='utf-8'))
    lua=P.runtime();catalog=P.plain(lua.eval("require('src.catalog')"))['maps']
    world=P.plain(lua.eval("require('data.world_art')"));dll,base=P.native_table()
    hubs={};stops=[];routes=[];held=[]
    for key,hub in seed['hubs'].items():
        current=dict(hub)
        if hub.get('map'):
            nodes=[node for node in world['zones'] if hub['map'] in node['maps']]
            if len(nodes)!=1:raise ValueError('World hub banner is ambiguous: '+key)
            b=nodes[0]['bounds'];current['world']=[b[2]+80,round((b[1]+b[3])/2,3)]
        hubs[key]=current
    for route in seed['routes']:
        ends=[]
        for side,other in [('a','b'),('b','a')]:
            hub_id=route[side];hub=hubs[hub_id];wid=route['wiki_'+side];target=route['wiki_'+other]
            stop={'id':route['id']+'-'+hub_id,'hub':hub_id,'category':route['category'],
                'title':hub['title']+' - '+route.get('service',('Ferry' if route['category']=='boat' else 'Airship'))+' to '+hubs[route[other]]['title'],
                'area':hub['title'],'wiki_map':wid}
            points=boarding_pulses(metadata[wid],target)
            if hub.get('map'):
                if len(points)!=1:raise ValueError('No unique boarding point for '+stop['id'])
                d=catalog[hub['map']]
                native=P.native_map(dll,base,d['key'],d['zone'],d['floor'],d['index'],d['name'],d['region'])
                t=native['transform'];f=abs(t['scale'])/5;lat,lng=points[0]
                if metadata[wid].get('bounds'):
                    x,y=round(lng*f-t['offset_x'],3),round(-lat*f-t['offset_y'],3)
                    method='wiki_pulse_native_transform'
                else:x,y=W.map_point(metadata[wid],points[0]);method='wiki_basic_native_artwork'
                if not (0<=x<=512 and 0<=y<=512):raise ValueError('Boarding point is outside native map')
                stop.update(map=d['key'],x=x,y=y,wiki_pulse=points[0],method=method)
            else:
                stop['method']='world_hub_only'
                held.append({'id':stop['id'],'reason':'Zone is outside the current native map catalog; world location only.'})
            stops.append(stop);ends.append(stop['id'])
        routes.append({k:route[k] for k in ('id','category','requirement','source')}|{'a':ends[0],'b':ends[1]})
    for pt in seed.get('points',[]):
        hubs[pt['id']]={'title':pt['title'],'area':pt['area'],'map':pt['map'],'world':pt['world']}
        d=catalog[pt['map']];wid=pt['wiki_map']
        native=P.native_map(dll,base,d['key'],d['zone'],d['floor'],d['index'],d['name'],d['region'])
        t=native['transform'];f=abs(t['scale'])/5
        if pt.get('entity'):
            matches=[e for e in metadata[wid].get('entities',[]) if e[1]==pt['entity']]
            if len(matches)!=1:raise ValueError('No unique entity point for '+pt['id'])
            gx,gz=matches[0][2],matches[0][4];method='wiki_entity_native_transform'
        else:
            gx,gz=pt['world_xy'];method='artwork_anchor_native_transform'
        x,y=round(gx*f-t['offset_x'],3),round(-gz*f-t['offset_y'],3)
        if not (0<=x<=512 and 0<=y<=512):raise ValueError('Point POI is outside native map: '+pt['id'])
        stops.append({'id':pt['id'],'hub':pt['id'],'category':pt['category'],'title':pt['title'],
            'area':pt['area'],'wiki_map':wid,'map':d['key'],'x':x,'y':y,'world_xy':[gx,gz],
            'requirement':pt['requirement'],'source':pt['source'],'method':method})
    output={'categories':seed['categories'],'hubs':hubs,'stops':stops,'routes':routes}
    corrections=Path(corrections_path) if corrections_path else ADDON/'annotations/poi/corrections.json'
    if corrections.exists():
        editor=lua.eval("require('src.poi_edits')")
        def table(value):
            if isinstance(value,dict):return lua.table_from({k:table(v) for k,v in value.items()})
            if isinstance(value,list):return lua.table_from([table(v) for v in value])
            return value
        changes=editor.validate(table(P.read(corrections)),table(output),table({'maps':catalog}),table(world))
        output=P.plain(editor.apply(table(output),changes,table({'maps':catalog})))
    path=ADDON/'data/pois.lua'
    payload=('-- Generated by tools/build_pois.py. Static transport locations; no live schedule claims.\nreturn '+P.lua_value(output)+'\n').encode()
    if write_outputs:path.write_bytes(payload)
    report={'routes':len(routes),'points':len(seed.get('points',[])),'world_hubs':len(hubs),'boarding_points':sum('map' in s for s in stops),
        'boarding_markers':len({(s['map'],s['category'],s['x'],s['y']) for s in stops if 'map' in s}),
        'world_only':held,'wiki_module_sha256':sha(wiki),'seed_sha256':sha(seed_path),'output_sha256':hashlib.sha256(payload).hexdigest(),
        'sources':sorted(set(r['source'] for r in routes)|set(p['source'] for p in seed.get('points',[]))),'notes':[
            'Mapped boarding points use wiki game-world coordinates projected through the installed native map table.',
            'World marker anchors are measured town/banner locations, not world-space boarding positions.',
            'Transport routes are separate from walking passages. No live schedules or pass ownership are inferred.']}
    if corrections.exists():
        report['corrections_sha256']=sha(corrections)
        report['corrections']={key:len(P.plain(changes)[key]) for key in ('world','stops')}
        report['notes'].append('Reviewed user corrections override projected/seed positions; source coordinates are retained as provenance.')
    if write_outputs:P.write(ADDON/'annotations/poi/build.json',report)
    print(f"Built {len(routes)} routes, {len(hubs)} hubs and {report['boarding_markers']} dock markers ({report['boarding_points']} endpoints)")
    return output,report

if __name__=='__main__':build()
