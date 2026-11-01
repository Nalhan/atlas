"""Build bounded native-resolution runtime pages from the connected map tiles."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ADDON=Path(__file__).resolve().parents[1]
DATA=ADDON/'annotations/imports/horizon'
ASSETS=ADDON/'assets/regions'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def tile_coordinates(layout):
    result=set()
    for left,top,right,bottom in layout['regions'].values():
        for y in range(top//256,(bottom-1)//256+1):
            for x in range(left//256,(right-1)//256+1):result.add((x,y))
    return sorted(result,key=lambda pair:(pair[1],pair[0]))

def crop_tiles(bounds,tiles):
    left,top,right,bottom=bounds
    output=Image.new('RGB',(right-left,bottom-top))
    for y in range(top//256,(bottom-1)//256+1):
        for x in range(left//256,(right-1)//256+1):
            tile=tiles[x,y]
            l,t,r,b=max(left,x*256),max(top,y*256),min(right,(x+1)*256),min(bottom,(y+1)*256)
            output.paste(tile.crop((l-x*256,t-y*256,r-x*256,b-y*256)),(l-left,t-top))
    return output

def build(p,lua,sources):
    layout=read(DATA/'regional-layout-z5.json');size=layout['texture_size'];zoom=layout['zoom_level']
    if zoom!=5 or size!=1024:raise ValueError('Unsupported connected-map layout')
    expected={row['path']:row for row in sources['files']}
    tiles={};source_files=[]
    for x,y in tile_coordinates(layout):
        path=DATA/f'tiles/{zoom}/{x}-{y}.jpeg';relative=path.relative_to(ADDON).as_posix()
        record=expected.get(relative)
        if not record or sha(path)!=record['sha256']:raise ValueError('Missing or changed connected-map tile: '+relative)
        with Image.open(path) as tile:
            if tile.size!=(256,256):raise ValueError('Incorrect source tile dimensions')
            tiles[x,y]=tile.convert('RGB')
        source_files.append(record)
    diagrams=lua.eval("require('src.regions').diagrams or require('data.regions')")
    boards={};assets={}
    for region,crop in layout['regions'].items():
        board=p.plain(diagrams[region]) if region!='ronfaure' else p.plain(lua.eval("require('src.region')"))
        width,height=crop[2]-crop[0],crop[3]-crop[1];pages=[]
        for y in range(0,height,size):
            for x in range(0,width,size):
                w,h=min(size,width-x),min(size,height-y)
                content=crop_tiles((crop[0]+x,crop[1]+y,crop[0]+x+w,crop[1]+y+h),tiles)
                page=Image.new('RGB',(size,size));page.paste(content)
                # Replicate edge pixels into padding to avoid a dark filtering fringe.
                if w<size:page.paste(content.crop((w-1,0,w,h)).resize((size-w,h)),(w,0))
                if h<size:page.paste(page.crop((0,h-1,size,h)).resize((size,size-h)),(0,h))
                path=ASSETS/f'horizon-z5-{region}-{x//size}-{y//size}.png';path.parent.mkdir(parents=True,exist_ok=True)
                page.save(path)
                relative=path.relative_to(ADDON).as_posix();assets[relative]=sha(path)
                pages.append({'path':relative,'x':x,'y':y,'w':w,'h':h,'texture_size':size})
        nodes={};by_map={}
        for key in board['order']:
            old=board['nodes'][key];maps=old['maps'];anchor=old.get('world_anchor') or layout['anchors'][maps[0]]
            l,t,r,b=anchor
            l-=crop[0];r-=crop[0];t-=crop[1];b-=crop[1]
            if not (0<=l<r<=width and 0<=t<b<=height):raise ValueError(f'{region}/{key}: banner outside crop')
            nodes[key]={'key':key,'title':old['title'],'maps':maps,'x':(l+r)/2,'y':(t+b)/2,'w':r-l,'h':b-t,
                'supplementary':maps[0] in layout['supplementary'] or old.get('supplementary',False),'external':old.get('external',False)}
            for map_key in maps:by_map[map_key]=key
        boards[region]={'id':region,'title':region.upper(),'width':width,'height':height,'nodes':nodes,
            'order':board['order'],'by_map':by_map,'artwork':{'pages':pages,'source_bounds':crop,'zoom_level':zoom}}
    (ADDON/'data/regional_art.lua').write_bytes(('-- Generated connected level-5 regional artwork and banner hit areas.\nreturn '+p.lua_value(boards)+'\n').encode())
    p.write(ASSETS/'SOURCES.json',{'source':'https://horizonffxi.wiki/Interactive_Map','zoom_level':zoom,
        'tile_size':256,'texture_size':size,'layout_sha256':sha(DATA/'regional-layout-z5.json'),
        'regions':layout['regions'],'assets':assets,'source_files':source_files,
        'pixel_policy':'Native source pixels, no resampling. Partial pages use edge-replicated padding outside their visible UVs.',
        'attribution':'HorizonXI Wiki / Remapster / Square Enix / FFXI Atlas'})
    return len(assets)
