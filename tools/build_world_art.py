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
    (ADDON/'data/world_art.lua').write_bytes(('-- Generated connected-world texture pyramid; all levels derive from native level 5.\nreturn '+p.lua_value(descriptor)+'\n').encode())
    p.write(output/'SOURCES.json',{'source':manifest['source'],'native_zoom':5,'master_sha256':manifest['outputs'][master.name]['sha256'],
        'assets':hashes,'attribution':manifest['attribution'],
        'pixel_policy':'LOD 5 preserves native pixels; lower LODs downsample the same connected artwork, preserving identical layout.'})
    print(f'Built full connected-world pyramid: {len(hashes)} bounded textures, 8192 × 8192 native reference')

if __name__=='__main__':build()
