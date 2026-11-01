"""Offline checks against LuaJIT and the locally installed client DATs.
Run from the Ashita Game directory: python addons/atlas/tests/verify.py
Requires Python, lupa and Pillow. The addon itself requires none of these.
"""
from pathlib import Path
import io
import re
import struct
from lupa.luajit21 import LuaRuntime
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
ADDON = ROOT / 'addons/atlas'
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute("package.path = ... .. '/?.lua;' .. package.path", ADDON.as_posix())
lua.execute("""
local C=require('src.catalog')
local N=require('src.navigation')
local seen={}
for _,p in ipairs(C.passages) do
    assert(not seen[p.id], 'Duplicate passage ID'); seen[p.id]=true
    for _,e in ipairs({p.a,p.b}) do
        assert(C.maps[e.map], 'Missing destination')
        assert(e.x>=0 and e.x<=512 and e.y>=0 and e.y<=512, 'Anchor outside map')
    end
end
local n=N.new()
N.go(n,'region'); N.go(n,'zone','west')
n.current.cx=210; n.current.cy=280; n.current.zoom=2.2
local before=n.current
for _,exit in ipairs(C.exits('west')) do
    N.travel(n,exit)
    assert(n.current.key==exit.target.map)
    assert(n.current.cx==exit.target.x and n.current.cy==exit.target.y)
    local ox,oy,s=N.transform(n.current,30,40,800,600,512,512)
    assert(math.abs(ox+exit.target.x*s-430)<0.00001)
    assert(math.abs(oy+exit.target.y*s-340)<0.00001)
    N.back(n); assert(n.current==before)
    N.forward(n); assert(n.current.key==exit.target.map)
    N.back(n)
end
for _,p in ipairs(C.passages) do
    local out
    for _,e in ipairs(C.exits(p.a.map)) do if e.id==p.id then out=e end end
    assert(out and out.target==p.b)
    local reverse
    for _,e in ipairs(C.exits(p.b.map)) do if e.id==p.id then reverse=e end end
    assert(p.one_way and reverse==nil or not p.one_way and reverse.target==p.a)
end
local v={cx=256,cy=256,zoom=1}
local ox,oy,s=N.transform(v,0,0,700,600,512,512)
local px,py=(150-ox)/s,(250-oy)/s
N.zoom_at(v,2,150,250,0,0,700,600,512,512)
ox,oy,s=N.transform(v,0,0,700,600,512,512)
assert(math.abs(ox+px*s-150)<0.00001 and math.abs(oy+py*s-250)<0.00001)
assert(C.find_player_map(100,0)=='west')
assert(C.find_player_map(100,99)==nil)
N.up(n); assert(n.current.level=='world' and n.current.focus)
""")
print('PASS: paired passage directions, one-way exits, arrival centering, history, zoom, floor isolation')

# Catch calls that aren't actually exported in this installed Ashita build.
sdk = (ROOT/'addons/libs/annotations/SDK/IGuiManager.lua').read_text(encoding='utf-8')
code = '\n'.join(p.read_text(encoding='utf-8') for p in ADDON.rglob('*.lua'))
for api in set(re.findall(r'imgui\.(\w+)\(',code)):
    assert f'function IGuiManager.{api}(' in sdk, f'Unrecognized ImGui API {api}'
print('PASS: UI APIs match installed Ashita SDK')

# Exercise the real client coordinate conversion with signed native table fields.
# The native floor call and Direct3D themselves still require the live game.
client_lua=LuaRuntime(unpack_returned_tuples=True)
client_lua.execute("package.path = ... .. '/?.lua;' .. package.path",ADDON.as_posix())
client_lua.execute("""
package.loaded.d3d8={};package.loaded['d3d8.d3dx8']={}
local bytes={[1000]=100,[1002]=0,[1004]=0,[1005]=251,[1008]=1,[1010]=65280,[1012]=65280}
ashita={memory={read_uint8=function(p) return bytes[p] end,
    read_uint16=function(p) return bytes[p] end,find=function() return 0 end}}
local M=require('src.client');M.init();assert(M.table_ptr==0)
M.table_ptr=1000
local def={zone=100,floor=0,index=0}
local e=M.entry(def);assert(e.scale==-5 and e.ox==-256 and e.dat==5313)
local x,y=M.position(def,{zone=100,floor=0,x=10,y=20})
assert(x==266 and y==236)
assert(M.position(def,{zone=101,floor=0,x=10,y=20})==nil)
assert(M.position(def,{zone=100,floor=1,x=10,y=20})==nil)
bytes[1000]=101;assert(M.entry(def)==nil)
local released={a=0,b=0,zone=0}
M.cache={
    ['asset:a']={owner={Release=function() released.a=released.a+1 end}},
    ['asset:b']={owner={Release=function() released.b=released.b+1 end}},
    west={owner={Release=function() released.zone=released.zone+1 end}}
}
M.keep_assets({'b'})
assert(not M.cache['asset:a'] and M.cache['asset:b'] and M.cache.west)
assert(released.a==1 and released.b==0 and released.zone==0)
M.clear();assert(released.a==1 and released.b==1 and released.zone==1)
assert(next(M.cache)==nil)
""")
print('PASS: actual client transform, signed scale/offsets, mismatched floor/zone/table rejection and regional texture release')

client_lua.execute("""
local M=require('src.client')
local entries={
    [1]={id=11,zone=100,index=1,name='Party'},
    [2]={id=12,zone=101,index=1,name='Remote'},
    [3]={id=13,zone=100,index=3,name='Reused index'},
    [4]={id=14,zone=100,index=4,name='Despawned'},
    [5]={id=11,zone=100,index=1,name='Duplicate'},
    [6]={id=16,zone=100,index=6,name='Alliance'},
    [17]={id=27,zone=100,index=17,name='Last alliance slot'}
}
local party={}
function party:GetMemberIsActive(i) return entries[i] and 1 or 0 end
function party:GetMemberServerId(i) return entries[i].id end
function party:GetMemberZone(i) return entries[i].zone end
function party:GetMemberName(i) return entries[i].name end
function party:GetMemberTargetIndex(i) return entries[i].index end
AshitaCore={GetMemoryManager=function() return {GetParty=function() return party end} end}
local entities={}
for i,entry in pairs(entries) do
    entities[i]={ServerId=i==3 and 999 or entry.id,Render={Flags0=i==4 and 0 or 1},
        Movement={LastPosition={X=i,Y=i*2,Z=0}},Heading=0}
end
GetEntity=function(i) return entities[i] end
M.floor_at=function() return 0 end
-- Repeated draws must observe movement even without any clock advancement.
local original_clock=os.clock;os.clock=function() return 1 end
local list=M.members({zone=100})
assert(#list==6) -- duplicate identity omitted, remote roster retained
assert(list[1].group=='party' and list[1].x==1 and list[1].floor==0)
assert(list[2].name=='Remote' and list[2].x==nil)
assert(list[3].x==nil and list[4].x==nil) -- reused / despawned entities
assert(list[5].group=='alliance' and list[5].x==6)
assert(list[6].slot==17 and list[6].x==17)
entities[1].Movement.LastPosition.X=40
entities[1].Movement.LastPosition.Y=50
entities[1].Heading=1.5
local refreshed=M.members({zone=100})
assert(refreshed[1].x==40 and refreshed[1].y==50 and refreshed[1].heading==1.5,
    'A consecutive draw reused stale member coordinates')
assert(list[1].x==1, 'Snapshots must not share mutable position data')
entities[1].ServerId=999
assert(M.members({zone=100})[1].x==nil, 'Reused entity must disappear immediately')
entities[1].ServerId=11
entities[1].Render.Flags0=0
assert(M.members({zone=100})[1].x==nil, 'Despawn must invalidate coordinates immediately')
entities[1].Render.Flags0=1
entries[1].zone=101
assert(M.members({zone=100})[1].x==nil, 'Remote member must lose coordinates immediately')
entries[1].zone=100
local moved=M.members({zone=101})
assert(moved~=list and moved[1].x==nil)
M.zoning=true;assert(#M.members({zone=100})==0);M.zoning=false
assert(M.members({zone=100})[1].x==40)
os.clock=original_clock
""")
print('PASS: party/alliance slots, per-draw movement, remote zones, reused identities, despawns, duplicates and zoning')

raw = LuaRuntime(encoding=None,unpack_returned_tuples=True)
raw.execute(b"package.path = ... .. '/?.lua;' .. package.path",ADDON.as_posix().encode())
wrap = raw.eval(b"require('src.dat_image').wrap")
ffxi = ROOT/'SquareEnix/FINAL FANTASY XI'
ftable=(ffxi/'FTABLE.DAT').read_bytes(); vtable=(ffxi/'VTABLE.DAT').read_bytes()
catalog=lua.eval("require('src.catalog')")
# Read the installed executable's original table to independently validate every
# curated index, including the Outpost cave floor missing from Boussole's index.
dll=(ffxi/'FFXiMain.dll').read_bytes()
candidates=[]
start=0
while True:
    p=dll.find(b'\x64\x00',start)
    if p<0:break
    start=p+1
    if p+42<len(dll) and struct.unpack_from('<HB',dll,p)==(100,0) and struct.unpack_from('<HB',dll,p+14)==(101,0) and struct.unpack_from('<HB',dll,p+28)==(102,0):
        candidates.append(p)
assert len(candidates)==1
base=candidates[0]
for key,definition in catalog['maps'].items():
    if definition['index'] is not None:
        zone,floor,_,flags,_,_,_,offset,_,_=struct.unpack_from('<HBBBbbBHhh',dll,base+int(definition['index'])*14)
        assert (zone,floor)==(definition['zone'],definition['floor']),(key,zone,floor)
        assert {0:5312,1:53295,2:54295}[flags&15]+offset==definition['dat'],key
lua.execute("""
local R=require('src.region');local C=require('src.catalog');local boards=require('src.regions')
for _,key in ipairs(C.order) do assert(boards.get(C.maps[key].region).by_map[key], 'Map missing from home region') end
for _,id in ipairs(boards.order) do
    local board=boards.get(id)
    for _,route in ipairs(board.routes(C)) do assert(board.nodes[route.a] and board.nodes[route.b]) end
end
assert(#C.siblings('outpost')==2 and #C.siblings('oubliette1')==3 and #C.siblings('north')==4 and #C.siblings('port_windurst')==5)
for _,key in ipairs(R.order) do
    local a,b=R.thumbnail_uv(R.nodes[key],1.5)
    assert(a[1]>=0 and a[2]>=0 and b[1]<=1 and b[2]<=1)
    assert(math.abs((b[1]-a[1])/(b[2]-a[2])-1.5)<0.00001)
end
local N=require('src.navigation');local state=N.new()
N.go(state,'zone','latheine');assert(state.current.region=='zulkheim')
N.up(state);assert(state.current.level=='world' and state.current.focus)
local e={source={map='latheine'},target={map='valkurm',x=10,y=20,arrival_x=15,arrival_y=30},id='focus-test'}
N.travel(state,e)
assert(state.current.cx==15 and state.current.cy==30)
assert(state.current.arrival.x==10 and state.current.arrival.y==20)
""")
print('PASS: all map entries match installed executable; all areas belong to region hubs')
count=0
for key,definition in [('world',{'dat':5312})]+list(catalog['maps'].items()):
    dat=definition['dat']
    if dat is None:
        continue
    packed=struct.unpack_from('<H',ftable,int(dat)*2)[0];rom=vtable[int(dat)]
    path=ffxi/('ROM' if rom==1 else f'ROM{rom}')/str(packed>>7)/f'{packed&127}.DAT'
    data=path.read_bytes()
    expected=b'conquest' if key=='world' else f'm_{definition["zone"]:03}_{definition["floor"]:02}'.encode()
    # Some historical DATs carry a different legacy name, but every chosen
    # original map here should resolve to its expected zone/floor image.
    alt=b'm_251_00' if key!='world' and (definition["zone"],definition["floor"])==(251,1) else expected
    assert expected in data[49:65] or alt in data[49:65], (key,expected,data[49:65])
    wrapped,w,h=wrap(data)
    assert wrapped, (key,w)
    im=Image.open(io.BytesIO(wrapped));im.load();assert im.size==(w,h)
    assert wrap(data[:120])[0] is None
    count+=1
    # Verify the actual installed XIPivot maps too (including HD DXT textures).
    for overlay in ['remapster','ffxivision']:
        hd=ROOT/'polplugins/DATs'/overlay/('ROM' if rom==1 else f'ROM{rom}')/str(packed>>7)/f'{packed&127}.DAT'
        if hd.exists():
            encoded,hw,hh=wrap(hd.read_bytes())
            assert encoded,(key,overlay,hw)
            image=Image.open(io.BytesIO(encoded));image.load();assert image.size==(hw,hh)
            count+=1
assert wrap(b'bad')[0] is None
print(f'PASS: {count} original / installed HD DAT images decoded, identities checked, truncation rejected')

# Compile every runtime source with LuaJIT 2.1 (the client uses LuaJIT).
for path in ADDON.rglob('*.lua'):
    lua.execute('assert(loadfile(...))',str(path))
print('PASS: all addon Lua sources compile with LuaJIT 2.1')
