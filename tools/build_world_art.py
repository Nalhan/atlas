"""Native connected-world paging with lower-resolution copies of the same layer."""
from pathlib import Path
import hashlib
import importlib.util
import json
from PIL import Image

ADDON=Path(__file__).resolve().parents[1]

def build():
    spec=importlib.util.spec_from_file_location('annotations',ADDON/'tools/annotations.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    source=ADDON/'exports/horizon-connected-z5';manifest=p.read(source/'manifest.json')
    master=source/'connected-world.png'
    if hashlib.sha256(master.read_bytes()).hexdigest()!=manifest['outputs'][master.name]['sha256']:
        raise ValueError('Connected-world master fingerprint changed')
    if (manifest['zoom_level'],manifest['width'],manifest['height'])!=(5,8192,8192):raise ValueError('Wrong world artwork layer')
    image=Image.open(master).convert('RGB');levels={};hashes={}
    output=ADDON/'assets/world';output.mkdir(parents=True,exist_ok=True)
    for zoom in (2,3,4,5):
        side=256*2**zoom;factor=8192//side
        current=image if zoom==5 else image.resize((side,side),Image.Resampling.LANCZOS)
        pages=[]
        for y in range(0,side,1024):
            for x in range(0,side,1024):
                path=output/f'connected-lod{zoom}-{x//1024}-{y//1024}.png'
                current.crop((x,y,x+1024,y+1024)).save(path)
                relative=path.relative_to(ADDON).as_posix();hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
                pages.append({'path':relative,'x':x*factor,'y':y*factor,'w':1024*factor,'h':1024*factor})
        levels[str(zoom)]=pages
    layout=p.read(ADDON/'annotations/imports/horizon/regional-layout-z5.json')
    lua=p.runtime();regional=lua.eval("require('data.regional_art')");zones={}
    for region_id in sorted(regional):
        board=regional[region_id]
        crop=board['artwork']['source_bounds']
        for node_id in sorted(board['nodes']):
            node=board['nodes'][node_id]
            bounds=[crop[1]+node['x']-node['w']/2,crop[2]+node['y']-node['h']/2,
                crop[1]+node['x']+node['w']/2,crop[2]+node['y']+node['h']/2]
            key=','.join(map(str,bounds));current=zones.setdefault(key,{'bounds':bounds,'title':node['title'],'maps':[],
                'supplementary':bool(node['supplementary'])})
            for _,map_key in node['maps'].items():
                if map_key not in current['maps']:current['maps'].append(map_key)
    descriptor={'width':8192,'height':8192,'native_zoom':5,'minimum_level':2,'levels':levels,
        'hotspots':layout['world_banners'],'regions':{key:{'bounds':bounds,'title':key.upper()} for key,bounds in layout['regions'].items()},
        'zones':sorted(zones.values(),key=lambda n:n['bounds']),'maximum_zoom':32}
    besieged_source=None
    aht_path=ADDON/'data/aht_urhgan.lua'
    if aht_path.exists():
        aht=p.plain(lua.eval("require('data.aht_urhgan')"));aht_layout=p.read(ADDON/'annotations/aht-urhgan/layout.json')
        native=p.ROOT/'SquareEnix/FINAL FANTASY XI'/aht_layout['native_path'];raw=native.read_bytes()
        if aht_layout['identity'].encode() not in raw[49:65]:raise ValueError('Besieged DAT identity changed')
        binary=p.runtime(True);encoded,w,h=binary.eval(b"require('src.dat_image').wrap")(raw)
        if not encoded or (w,h)!=(512,512):raise ValueError('Unexpected Besieged map format')
        left,top,width,height=aht_layout['placement'];sx,sy=width/512,height/512
        descriptor['width']=aht_layout['world_width']
        descriptor['besieged']={'key':'besieged','dat':aht_layout['dat'],'x':left,'y':top,'w':width,'h':height}
        descriptor['regions']['besieged']={'title':'AHT URHGAN','bounds':[left,top,left+width,top+height]}
        descriptor['labels']=[{'title':'AHT URHGAN','x':left+width/2,'y':top+60,'kind':'sheet'}]
        for region,info in aht_layout['regions'].items():
            x1,y1,x2,y2=info['bounds'];bounds=[left+x1*sx,top+y1*sy,left+x2*sx,top+y2*sy]
            descriptor['regions'][region]={'title':info['title'],'bounds':bounds}
            descriptor['hotspots'][region]=bounds
            descriptor['labels'].append({'title':info['title'],'x':left+info['label'][0]*sx,'y':top+info['label'][1]*sy,'kind':'region'})
        groups={}
        for definition in aht['maps']:groups.setdefault(definition['zone'],[]).append(definition)
        for zone,definitions in sorted(groups.items()):
            point=aht_layout['zones'][str(zone)];x,y=left+point[0]*sx,top+point[1]*sy
            title=definitions[0]['name'].split(' / ')[0]
            descriptor['zones'].append({'title':title,'bounds':[x-250,y-62,x+250,y+62],
                'maps':[d['key'] for d in definitions],'supplementary':True,'overview':'besieged'})
        besieged_source={'path':aht_layout['native_path'],'dat':aht_layout['dat'],
            'identity':aht_layout['identity'],'sha256':hashlib.sha256(raw).hexdigest(),'native_dimensions':[w,h],
            'placement':aht_layout['placement'],'layout_sha256':hashlib.sha256((ADDON/'annotations/aht-urhgan/layout.json').read_bytes()).hexdigest()}
    additions_path=ADDON/'annotations/world-selectors/additions.json'
    if additions_path.exists():
        catalog=p.plain(lua.eval("require('src.catalog')"))['maps']
        additions=p.read(additions_path)
        for extra in additions['nodes']:
            assert all(key in catalog for key in extra['maps']),'Unknown supplementary map'
            for node in descriptor['zones']:
                node_id=node.get('id') or 'zone-'+str(catalog[node['maps'][0]]['zone'])
                if node_id==extra['split_from']:
                    node['maps']=[key for key in node['maps'] if key not in extra['maps']]
                    assert node['maps'],'Split would leave an empty world selector'
            descriptor['zones'].append({k:extra[k] for k in ('id','title','bounds','maps','supplementary')})
    selector_path=ADDON/'annotations/world-selectors/corrections.json'
    selector_sha=None
    if selector_path.exists():
        edits=lua.eval("require('src.world_selectors')")
        def table(value):
            if isinstance(value,dict):return lua.table_from({k:table(v) for k,v in value.items()})
            if isinstance(value,list):return lua.table_from([table(v) for v in value])
            return value
        changes=edits.validate(table(p.read(selector_path)),table(descriptor))
        descriptor=p.plain(edits.correct(table(descriptor),changes))
        selector_sha=hashlib.sha256(selector_path.read_bytes()).hexdigest()
    (ADDON/'data/world_art.lua').write_bytes(('-- Generated connected-world texture pyramid; all levels derive from native level 5.\nreturn '+p.lua_value(descriptor)+'\n').encode())
    p.write(output/'SOURCES.json',{'source':manifest['source'],'native_zoom':5,'master_sha256':manifest['outputs'][master.name]['sha256'],
        'assets':hashes,'attribution':manifest['attribution'],'besieged':besieged_source,
        **({'world_selectors_sha256':selector_sha} if selector_sha else {}),
        **({'world_selector_additions_sha256':hashlib.sha256(additions_path.read_bytes()).hexdigest()} if additions_path.exists() else {}),
        'pixel_policy':'LOD 5 preserves native pixels; lower LODs downsample the same connected artwork, preserving identical layout.'})
    print(f'Built full connected-world pyramid: {len(hashes)} bounded textures, 8192 × 8192 native reference')

if __name__=='__main__':build()
