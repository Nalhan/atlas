"""Export a native wiki tile layer, with exact geometry and an offline viewer.

Unlike an enlarged lower-zoom image or browser screenshot, each source tile is
decoded once and pasted at its native location. Source tiles remain cached.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import base64
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from PIL import Image

ADDON=Path(__file__).resolve().parents[1]
CACHE=ADDON/'annotations/imports/horizon/tiles'
BASE='https://horizonffxi.wiki/w/extensions/FFXIMap/maps/tiles'
TILE_SIZE=256
DETAIL_CROPS={5:{'ronfaure-detail.png':[2100,2320,3900,3700]}}

def sha(data):return hashlib.sha256(data).hexdigest()

def tile_bounds(rect,tile_size=TILE_SIZE):
    """Half-open pixel crop -> inclusive/exclusive tile range, avoiding seams."""
    left,top,right,bottom=rect
    if left<0 or top<0 or right<=left or bottom<=top:raise ValueError('Invalid pixel bounds')
    return (int(left//tile_size),int(top//tile_size),int((right-1)//tile_size)+1,int((bottom-1)//tile_size)+1)

def fetch_tile(zoom,x,y):
    path=CACHE/str(zoom)/f'{x}-{y}.jpeg';path.parent.mkdir(parents=True,exist_ok=True)
    url=f'{BASE}/{zoom}/{x}/{y}.jpeg'
    for attempt in range(3):
        try:
            cached=path.exists()
            if cached:data=path.read_bytes()
            else:
                req=urllib.request.Request(url,headers={'User-Agent':'AtlasMapPrototype/0.4 (bounded, cached artwork export)'})
                with urllib.request.urlopen(req,timeout=45) as response:data=response.read()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if image.size!=(TILE_SIZE,TILE_SIZE) or image.format!='JPEG':raise ValueError('Unexpected tile format/size: '+url)
            if not cached:
                temporary=path.with_suffix('.part');temporary.write_bytes(data);temporary.replace(path)
            return {'x':x,'y':y,'url':url,'cached_path':path.relative_to(ADDON).as_posix(),
                'sha256':sha(data),'bytes':len(data)}
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:raise
            time.sleep(min(20,float(exc.headers.get('Retry-After','1'))*(attempt+1)))
        except (OSError,ValueError):
            if path.exists() or attempt==2:raise
            time.sleep(attempt+1)

def assemble(zoom,tiles):
    side=TILE_SIZE*(2**zoom);expected={(x,y) for x in range(2**zoom) for y in range(2**zoom)}
    if {(r['x'],r['y']) for r in tiles}!=expected or len(tiles)!=len(expected):
        raise ValueError('Incomplete or duplicate tile coverage')
    image=Image.new('RGB',(side,side))
    for row in sorted(tiles,key=lambda r:(r['y'],r['x'])):
        path=ADDON/row['cached_path'];data=path.read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('Source tile changed: '+str(path))
        with Image.open(io.BytesIO(data)) as tile:image.paste(tile.convert('RGB'),(row['x']*TILE_SIZE,row['y']*TILE_SIZE))
    return image

def write_viewer(output,preview,crops):
    # Embedding the viewing image makes file:// previews self-contained and
    # avoids external libraries, network requests and local-origin fetch issues.
    image_data=base64.b64encode(preview.read_bytes()).decode('ascii')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connected Vana’diel map</title><style>
*{box-sizing:border-box}body{margin:0;background:#1e3028;color:#eddfc2;font:15px system-ui,sans-serif;overflow:hidden}
header{height:58px;display:flex;align-items:center;gap:12px;padding:10px 16px;background:#17261f;border-bottom:1px solid #506353}
strong{margin-right:auto;font-weight:550}button,a{border:1px solid #69735e;border-radius:5px;color:inherit;background:#2a3b2f;padding:7px 13px;text-decoration:none;font:inherit;cursor:pointer}
button:hover,a:hover{background:#41513d}canvas{display:block;touch-action:none;cursor:grab}canvas:active{cursor:grabbing}
footer{position:fixed;left:12px;bottom:9px;color:#d4d5bf;font-size:12px;text-shadow:0 1px 3px #000;pointer-events:none}
</style><header><strong>Connected Vana’diel</strong><button id="fit">Fit</button><button id="actual">Actual size</button>
REGION_BUTTON<a href="connected-world.png" download>Full PNG</a><span id="zoom"></span></header><canvas id="map"></canvas>
<footer>Wheel to zoom · Drag to pan · HorizonXI Wiki / Remapster / Square Enix / FFXI Atlas</footer>
<script>
const canvas=document.getElementById('map'),ctx=canvas.getContext('2d'),image=new Image();
let width=0,height=0,scale=1,ox=0,oy=0,ready=false,drag=null;
function draw(){if(!ready)return;ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);ctx.fillStyle='#1e3028';ctx.fillRect(0,0,width,height);ctx.drawImage(image,ox,oy,image.width*scale,image.height*scale);document.getElementById('zoom').textContent=Math.round(scale*100)+'%'}
function fit(){if(!ready)return;scale=Math.min(width/image.width,height/image.height);ox=(width-image.width*scale)/2;oy=(height-image.height*scale)/2;draw()}
function resize(){width=innerWidth;height=innerHeight-58;canvas.width=width*devicePixelRatio;canvas.height=height*devicePixelRatio;canvas.style.width=width+'px';canvas.style.height=height+'px';fit()}
function zoomAt(next,x,y){const px=(x-ox)/scale,py=(y-oy)/scale;scale=Math.max(.025,Math.min(4,next));ox=x-px*scale;oy=y-py*scale;draw()}
canvas.addEventListener('wheel',e=>{e.preventDefault();zoomAt(scale*Math.exp(-e.deltaY*.0015),e.offsetX,e.offsetY)},{passive:false});
canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,ox,oy};canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{if(drag){ox=drag.ox+e.clientX-drag.x;oy=drag.oy+e.clientY-drag.y;draw()}});
canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
document.getElementById('fit').onclick=fit;document.getElementById('actual').onclick=()=>zoomAt(1,width/2,height/2);
REGION_HANDLER
window.addEventListener('resize',resize);image.onload=()=>{ready=true;resize()};image.src='data:image/jpeg;base64,IMAGE_DATA';resize();
</script></html>'''.replace('IMAGE_DATA',image_data)
    if 'ronfaure-detail.png' in crops:
        bounds=json.dumps(crops['ronfaure-detail.png']['bounds_pixels'])
        html=html.replace('REGION_BUTTON','<button id="ronfaure">Ronfaure</button>')
        html=html.replace('REGION_HANDLER',f"document.getElementById('ronfaure').onclick=()=>{{const r={bounds};scale=Math.min(width/(r[2]-r[0]),height/(r[3]-r[1]));ox=width/2-(r[0]+r[2])/2*scale;oy=height/2-(r[1]+r[3])/2*scale;draw()}};")
    else:html=html.replace('REGION_BUTTON','').replace('REGION_HANDLER','')
    (output/'view-map.html').write_text(html,encoding='utf-8')

def verify_export(output):
    output=Path(output);manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    expected={(x,y) for x in range(manifest['grid'][0]) for y in range(manifest['grid'][1])}
    rows=manifest['tiles']
    if len(rows)!=len(expected) or {(r['x'],r['y']) for r in rows}!=expected:raise ValueError('Missing or duplicate source tiles')
    with Image.open(output/'connected-world.png') as image:
        image=image.convert('RGB')
        if image.size!=(manifest['width'],manifest['height']):raise ValueError('Export dimensions changed')
        for row in rows:
            path=ADDON/row['cached_path'];data=path.read_bytes()
            if sha(data)!=row['sha256']:raise ValueError('Source hash changed: '+str(path))
            with Image.open(io.BytesIO(data)) as tile:
                x,y=row['x']*TILE_SIZE,row['y']*TILE_SIZE
                if image.crop((x,y,x+TILE_SIZE,y+TILE_SIZE)).tobytes()!=tile.convert('RGB').tobytes():
                    raise ValueError(f'Export pixels differ at tile {row["x"]},{row["y"]}')
        for name,crop in manifest.get('crops',{}).items():
            path=output/name
            if sha(path.read_bytes())!=crop['sha256']:raise ValueError('Crop hash changed: '+name)
            with Image.open(path) as detail:
                if detail.convert('RGB').tobytes()!=image.crop(crop['bounds_pixels']).tobytes():raise ValueError('Crop pixels differ: '+name)
    for name,record in manifest['outputs'].items():
        if sha((output/name).read_bytes())!=record['sha256']:raise ValueError('Output hash changed: '+name)
    audit={'tile_count':len(rows),'pixel_matches':len(rows),'dimensions':[manifest['width'],manifest['height']],
        'missing_tiles':0,'native_pixel_assembly_verified':True,
        'manifest_sha256':sha((output/'manifest.json').read_bytes())}
    (output/'verification.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print('PASS: every source tile and detail crop matches the full PNG pixel-for-pixel',flush=True)
    return audit

def export(zoom,output):
    if zoom not in (4,5,6):raise ValueError('Only inspected detail levels 4–6 are supported')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    pairs=[(x,y) for y in range(2**zoom) for x in range(2**zoom)]
    rows=[];total=len(pairs);started=time.monotonic()
    print(f'Exporting native level {zoom}: {total} tiles, {TILE_SIZE*2**zoom} × {TILE_SIZE*2**zoom} pixels',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch_tile,zoom,x,y):(x,y) for x,y in pairs}
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows)%64==0 or len(rows)==total:print(f'Tiles ready: {len(rows)}/{total}',flush=True)
    rows.sort(key=lambda r:(r['y'],r['x']))
    image=assemble(zoom,rows)
    print('Assembling lossless PNG and portable viewing copy',flush=True)
    full=output/'connected-world.png';image.save(full,compress_level=6)
    # This smaller viewing copy preserves full dimensions; canonical PNG retains
    # the source JPEG decode without another lossy encoding.
    viewing=output/'connected-world.jpg';image.save(viewing,quality=94,subsampling=0)
    overview=image.copy();overview.thumbnail((2048,2048),Image.Resampling.LANCZOS)
    overview.save(output/'overview.jpg',quality=92,subsampling=0)
    crops={}
    for name,bounds in DETAIL_CROPS.get(zoom,{}).items():
        path=output/name;image.crop(bounds).save(path)
        crops[name]={'bounds_pixels':bounds,'width':bounds[2]-bounds[0],'height':bounds[3]-bounds[1],
            'resampled':False,'sha256':sha(path.read_bytes())}
    write_viewer(output,viewing,crops)
    manifest={'schema_version':1,'source':'https://horizonffxi.wiki/Interactive_Map',
        'source_tile_template':BASE+'/{z}/{x}/{y}.jpeg','zoom_level':zoom,'tile_size':TILE_SIZE,
        'grid':[2**zoom,2**zoom],'width':image.width,'height':image.height,
        'pixel_origin':'top-left','world_bounds_lat_lng':[[-256,0],[0,256]],
        'world_to_pixel':{'x':'longitude * 2^zoom','y':'-latitude * 2^zoom'},
        'encoding':'connected-world.png retains decoded native tile pixels; JPG/viewer is a viewing copy',
        'attribution':'HorizonXI Wiki interactive map; Remapster, Square Enix, FFXI Atlas',
        'exported_utc':datetime.now(timezone.utc).isoformat(),'tiles':rows,'crops':crops,
        'outputs':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in (full,viewing,output/'overview.jpg')},
        'elapsed_seconds':round(time.monotonic()-started,2)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'README.md').write_text(f'''# Connected world artwork — native level {zoom}

Open `view-map.html` for an offline pan/zoom viewer. `connected-world.png` is the
full {image.width} × {image.height} export. `overview.jpg` is only a reduced preview.
The JPG/viewer is a smaller viewing copy; use PNG for further artwork processing.
The Ronfaure detail is a native-resolution crop with its bounds in the manifest.

All {total} original 256 × 256 tiles are placed without scaling or screenshot
stitching. Pixel origin is top-left. The manifest records exact source URLs,
hashes, tile positions and the wiki's world-coordinate transform.

This full image is an authoring master. For the D3D8 addon, cut bounded textures
from this master or stream the original tiles instead of uploading one giant
texture. Changing zoom level can change the artwork itself; do not assume that
the older banner hit areas identify individual zone outlines in this layer.

Source: https://horizonffxi.wiki/Interactive_Map
Artwork credits: HorizonXI Wiki / Remapster / Square Enix / FFXI Atlas.
''',encoding='utf-8')
    verify_export(output)
    print(json.dumps({'output':str(output.resolve()),'zoom':zoom,'pixels':image.size,
        'tiles':total,'source_bytes':sum(r['bytes'] for r in rows),'png_bytes':full.stat().st_size,
        'elapsed_seconds':manifest['elapsed_seconds']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--zoom',type=int,default=5)
    parser.add_argument('--output',type=Path,default=ADDON/'exports/horizon-connected-z5')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    verify_export(args.output) if args.verify_only else export(args.zoom,args.output)
