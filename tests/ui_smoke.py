"""Exercise actual Atlas UI callbacks without the game; optionally render draw calls.
The adapter does not emulate native client memory, Pivot or Direct3D.
"""
from pathlib import Path
import argparse
import io
import math
import struct
import tempfile
from lupa.luajit21 import LuaRuntime
from PIL import Image,ImageDraw,ImageFont,ImageChops
ROOT=Path(__file__).resolve().parents[3]
ADDON=ROOT/'addons/atlas'
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute("package.path = ... .. '/?.lua;' .. package.path",ADDON.as_posix())
lua.execute("package.path = ... .. '/?.lua;' .. package.path",(ROOT/'addons/libs').as_posix())
label_preview_fonts={}
def label_preview_font(size):
    size=int(size)
    if size not in label_preview_fonts:label_preview_fonts[size]=ImageFont.truetype('C:/Windows/Fonts/georgiab.ttf',size)
    return label_preview_fonts[size]
def measure_label(value,size):
    font=label_preview_font(size);lines=value.split('\n')
    return max(font.getlength(line) for line in lines),len(lines)*size
lua.globals().measure_label=measure_label
lua.execute(r"""
addon={};ImGuiCond_FirstUseEver=0;ImGuiWindowFlags_NoScrollbar=0
T=function(value) return value end
ImGuiWindowFlags_NoScrollWithMouse=0;ImGuiChildFlags_None=0
ImGuiCol_Button=0;ImGuiCol_WindowBg=0;ImGuiMouseCursor_Hand=7
ImGuiCol_ButtonHovered=0;ImGuiCol_ButtonActive=0;ImGuiCol_FrameBg=0;ImGuiCol_PopupBg=0
bit=require('bit');callbacks={};calls={};click_button=nil;select_label=nil
hover=false;release=false;mouse_x=0;mouse_y=0;window_open=true
viewport_w=1100;viewport_h=760;dragging=false;mouse_clicked=false;drag_dx=0;drag_dy=0
mouse_down=false
ashita={events={register=function(event,_,fn) callbacks[event]=fn end}}
package.loaded.common=true
local draw=setmetatable({}, {__index=function(_,name)
    return function(_,...) local call={name,...};call.font_size=font_size;call.font_family=font_family;calls[#calls+1]=call end
end})
local I={}
I.Begin=function() return window_open end;I.End=function() end
I.BeginChild=function() return true end;I.EndChild=function() end
I.BeginTooltip=function() end;I.EndTooltip=function() end
I.SetNextWindowSize=function() end;I.SetNextWindowSizeConstraints=function() end
I.SetNextWindowFocus=function() focus_requests=(focus_requests or 0)+1 end
I.TextUnformatted=function() end;I.Separator=function() end;I.SameLine=function() end
I.BeginDisabled=function(value) disabled=value end;I.EndDisabled=function() disabled=false end
I.Button=function(label) return not disabled and label==click_button end
I.Selectable=function(label) return label==select_label end
I.SetNextItemWidth=function() end;I.InputTextWithHint=function() return false end
font_size=14;font_family='default';font_stack={}
I.AddFontFromFileTTF=function(path,size) font_loads=(font_loads or 0)+1;return path end
I.GetFont=function() return 'default' end
I.PushFont=function(family,size) font_stack[#font_stack+1]={font_size,font_family};font_size=size;font_family=family end
I.PopFont=function() local old=table.remove(font_stack);font_size=old[1];font_family=old[2] end
I.BeginCombo=function() return combo_open or false end;I.EndCombo=function() end
I.OpenPopup=function(id) opened_popup=id end
I.BeginPopup=function(id) return opened_popup==id end
I.EndPopup=function() end;I.CloseCurrentPopup=function() opened_popup=nil end
I.Checkbox=function() return false end;I.PushStyleColor=function() end;I.PopStyleColor=function() end
I.SetMouseCursor=function() end;I.SetClipboardText=function(value) clipboard=value end
I.IsItemHovered=function() return hover end;I.IsItemActive=function() return dragging end
I.IsMouseReleased=function(b) return b==0 and release end
I.IsMouseClicked=function(b) return b==0 and mouse_clicked end
I.IsMouseDown=function(b) return b==0 and mouse_down end
I.IsMouseDragging=function() return dragging end
I.GetMouseDragDelta=function() return drag_dx,drag_dy end
I.GetCursorScreenPos=function() return 0,0 end
I.GetContentRegionAvail=function() return viewport_w,viewport_h end
I.GetMousePos=function() return mouse_x,mouse_y end
I.GetIO=function() return {MouseWheel=wheel or 0} end
I.InvisibleButton=function() return false end
I.GetWindowDrawList=function() return draw end
I.CalcTextSize=function(t)
    if font_family~='default' then return measure_label(t,font_size) end
    local width,n=0,0;for line in (t..'\n'):gmatch('(.-)\n') do width=math.max(width,#line*font_size*.5);n=n+1 end
    return width,n*font_size
end
package.loaded.imgui=I
function restore_people()
    test_player={zone=100,floor=0,x=0,y=0,z=0,heading=0,name='Doughmaker',mapx=250,mapy=260}
    test_members={
        {zone=100,floor=0,x=0,y=0,name='Avery',group='party',heading=0.7,mapx=236,mapy=243},
        {zone=101,name='Rowan',group='party'},
        {zone=100,floor=0,x=0,y=0,name='Mira',group='alliance',heading=2,mapx=280,mapy=272},
        {zone=100,floor=1,x=0,y=0,name='Different floor',group='alliance',heading=0,mapx=260,mapy=250}
    }
end
restore_people()
asset_cache={};asset_loads=0
package.loaded['src.client']={
    init=function() end,clear=function() asset_cache={} end,
    peek_asset=function(path) return asset_cache[path] end,
    asset=function(path)
        if not asset_cache[path] then
            asset_loads=asset_loads+1
            asset_cache[path]=missing_art and {error='Test missing artwork'} or {id=path,width=1024,height=1024}
        end
        return asset_cache[path]
    end,
    keep_assets=function(paths,limit)
        active_assets=paths;local keep={};for _,path in ipairs(paths) do keep[path]=true end
        local count=0;for _ in pairs(asset_cache) do count=count+1 end
        for path in pairs(asset_cache) do
            if not keep[path] and (not limit or count>limit) then asset_cache[path]=nil;count=count-1 end
        end
    end,
    player=function() return test_player end,
    members=function() return test_members end,
    position=function(def,p)
        if p and p.x~=nil and def.zone==p.zone and def.floor==p.floor then return p.mapx,p.mapy end
    end,
    texture=function(def)
        if def.asset then return {id=def.asset,width=512,height=512} end
        if not def.dat then return nil,'No standard map' end
        if missing_texture then return {error='Test missing texture'} end
        return {id=def.dat,width=512,height=512,remapster=not plain_texture and (preview_flags==nil or preview_flags[def.dat])}
    end
}
function command(value)
    local e={command=setmetatable({}, {__index={args=function() return {'/atlas',value} end}})}
    callbacks.command(e);assert(e.blocked)
end
function click_at(x,y)
    hover=true;release=true;mouse_x=x;mouse_y=y;callbacks.d3d_present();release=false;hover=false
end
""")
lua.execute('assert(loadfile(...))()',str(ADDON/'atlas.lua'))
lua.execute(r"""
local U=require('src.ui');local N=require('src.navigation');local C=require('src.catalog')
test_state=U.state
callbacks.load();callbacks.d3d_present()
assert(not U.visible[1] and #calls==0 and test_state.current.level=='world')
command('');callbacks.d3d_present()
assert(test_state.current.level=='zone' and test_state.current.key=='west')
assert(focus_requests==1,'Atlas did not rise when opened')
callbacks.d3d_present();assert(focus_requests==1,'Atlas repeatedly stole focus from other menus')
assert(test_state.current.cx==250 and test_state.current.cy==260)
-- Reopening follows the player's new floor; it does not keep the last browsed map.
command('hide');test_player.zone=C.maps.oubliette1.zone;test_player.floor=C.maps.oubliette1.floor
test_player.mapx=120;test_player.mapy=180
command('');callbacks.d3d_present()
assert(test_state.current.key=='oubliette1')
assert(test_state.current.cx==120 and test_state.current.cy==180)
-- An open during zoning waits for a player snapshot, then locates once only.
command('hide');test_player=nil;command('show');callbacks.d3d_present()
assert(U.pending_locate)
restore_people();test_player.floor=nil;callbacks.d3d_present();assert(U.pending_locate)
test_player.floor=0;callbacks.d3d_present()
assert(not U.pending_locate and test_state.current.key=='west')
N.go(test_state,'zone','east');callbacks.d3d_present()
assert(test_state.current.key=='east')
-- Unsupported areas fall back to Conquest; explicit destinations override default.
test_player.zone=999;command('show');callbacks.d3d_present()
assert(test_state.current.level=='world' and not U.pending_locate)
restore_people();command('show');command('norvallen');callbacks.d3d_present()
assert(test_state.current.level=='world' and test_state.current.focus)
command('world');click_button='Fit';callbacks.d3d_present();click_button=nil
assert(test_state.current.level=='world')
local W=require('src.world').data
local ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,W.width,W.height)
local banner=W.hotspots.ronfaure
click_at(ox+(banner[1]+banner[3])/2*s,oy+(banner[2]+banner[4])/2*s)
assert(test_state.current.level=='world' and test_state.current.zoom==1)
command('ronfaure');callbacks.d3d_present()
ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,W.width,W.height)
for _,node in ipairs(W.zones) do
    if node.maps[1]=='west' then
        local b=node.bounds;click_at(ox+(b[1]+b[3])/2*s,oy+(b[2]+b[4])/2*s);break
    end
end
assert(test_state.current.key=='west')
-- Every West Ronfaure exit is reachable by its canvas hotspot. Close gates
-- must offer a choice instead of making one entrance impossible to select.
for _,exit in ipairs(C.exits('west')) do
    N.go(test_state,'zone','west');opened_popup=nil;callbacks.d3d_present()
    ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    click_at(ox+exit.source.x*s,oy+exit.source.y*s)
    if opened_popup then
        local found
        for i,e in ipairs(U.choices) do
            if e.id==exit.id then
                local name=C.maps[e.source.map].name..' > '..C.maps[e.target.map].name
                if e.source.label then name=name..' / '..e.source.label end
                select_label=name..'##passage-'..i;found=true
            end
        end
        assert(found);callbacks.d3d_present();select_label=nil
    end
    assert(test_state.current.key==exit.target.map,exit.id)
    assert(test_state.current.arrival.passage==exit.id)
end
-- Direct map search and floor / district tabs replace the sidebar.
combo_open=true;select_label=C.maps.oubliette1.name..'##area-oubliette1'
callbacks.d3d_present();combo_open=false;select_label=nil;assert(test_state.current.key=='oubliette1')
click_button='Lower tunnels##floor-oubliette3';callbacks.d3d_present();click_button=nil
assert(test_state.current.key=='oubliette3')
for _,key in ipairs(C.order) do N.go(test_state,'zone',key);callbacks.d3d_present() end
-- Drive every newly reviewed passage through actual canvas hit testing in both
-- allowed directions, including separate badge coordinates and focus anchors.
reviewed_paths_tested=0
for _,p in ipairs(C.passages) do
    if p.status=='artwork_reviewed' or p.status=='source_correlated' then
        local edges={{source=p.a,target=p.b}}
        if not p.one_way then edges[#edges+1]={source=p.b,target=p.a} end
        for _,edge in ipairs(edges) do
            N.go(test_state,'zone',edge.source.map);opened_popup=nil;callbacks.d3d_present()
            ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
            click_at(ox+edge.source.x*s,oy+edge.source.y*s)
            if opened_popup then
                local found
                for i,e in ipairs(U.choices) do
                    if e.id==p.id then
                        local name=C.maps[e.source.map].name..' > '..C.maps[e.target.map].name
                        if e.target.component and e.target.component~='main' then name=name..' ['..e.target.component:gsub('_',' ')..']' end
                        if e.source.label then name=name..' / '..e.source.label end
                        select_label=name..'##passage-'..i;found=true
                    end
                end
                assert(found,p.id..' absent from choice');callbacks.d3d_present();select_label=nil
            end
            assert(test_state.current.key==edge.target.map,p.id..' target')
            assert(test_state.current.cx==(edge.target.arrival_x or edge.target.x),p.id..' focus x')
            assert(test_state.current.cy==(edge.target.arrival_y or edge.target.y),p.id..' focus y')
            assert(test_state.current.arrival.passage==p.id)
            reviewed_paths_tested=reviewed_paths_tested+1
        end
    end
end
for id in pairs(require('src.world').data.regions) do
    command(id);callbacks.d3d_present()
    assert(test_state.current.level=='world' and test_state.current.focus and test_state.current.zoom>1)
end
command('here');callbacks.d3d_present();assert(test_state.current.key=='west')
-- Same-frame movement after the drag threshold must not jump or drift.
hover=true;dragging=true;mouse_clicked=true;drag_dx=12;drag_dy=7
local before=test_state.current.cx;callbacks.d3d_present();local moved=test_state.current.cx
assert(moved<before);mouse_clicked=false;callbacks.d3d_present();assert(test_state.current.cx==moved)
release=true;callbacks.d3d_present();release=false;hover=false;dragging=false
-- Party / alliance toggles alter the actual marker draws, not the data source.
local function triangles()
    local n=0;for _,c in ipairs(calls) do if c[1]=='AddTriangleFilled' then n=n+1 end end;return n
end
N.go(test_state,'zone','west');calls={};callbacks.d3d_present();local all=triangles()
U.party[1]=false;calls={};callbacks.d3d_present();assert(triangles()==all-1)
U.alliance[1]=false;calls={};callbacks.d3d_present();assert(triangles()==all-2)
U.party[1]=true;U.alliance[1]=true
-- All artwork uses invisible hits: no replacement exit shapes or text at rest.
test_player=nil;test_members={};N.go(test_state,'zone','fort');calls={};callbacks.d3d_present()
assert(triangles()==0)
for _,plain in ipairs({false,true}) do
    plain_texture=plain;calls={};callbacks.d3d_present()
    assert(triangles()==0)
    for _,c in ipairs(calls) do assert(c[1]~='AddText', 'Exit text painted over the map') end
    local exit=C.exits('fort')[1]
    ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    hover=true;mouse_x=ox+exit.source.x*s;mouse_y=oy+exit.source.y*s
    calls={};callbacks.d3d_present();assert(triangles()==0)
    local lines=0;for _,c in ipairs(calls) do if c[1]=='AddLine' then lines=lines+1 end end
    assert(lines==8, 'Hover should add only the corner outline')
    mouse_clicked=true;callbacks.d3d_present();mouse_clicked=false
    click_at(mouse_x,mouse_y)
    if opened_popup then
        local found=false
        for _,choice in ipairs(U.choices) do if choice.id==exit.id then found=true end end
        assert(found);opened_popup=nil
    else assert(test_state.current.key==exit.target.map) end
    N.go(test_state,'zone','fort')
end
plain_texture=false;hover=false
N.go(test_state,'zone','horlais');calls={};callbacks.d3d_present()
local link=false
for _,c in ipairs(calls) do if c[1]=='AddText' and c[4]=='Hot springs' then link=true end end
assert(link, 'An uncharted map must still expose a plain text exit link')
command('here');callbacks.d3d_present()
missing_texture=true;command('world');click_button='Fit';callbacks.d3d_present();click_button=nil;missing_texture=false
window_open=false;callbacks.d3d_present();window_open=true
callbacks.packet_in({id=0x00B});callbacks.packet_in({id=0x00A})
command('hide');callbacks.d3d_present();command('show');restore_people()
""")
print(f'PASS: current-map startup/reopen, zoning deferral, explicit destinations, actual canvas navigation, {lua.globals().reviewed_paths_tested} reviewed route directions, clustered gates, area picker, floor tabs, stable pan, group toggles and invisible exit controls')
lua.execute(r"""
local U=require('src.ui');local N=require('src.navigation');local C=require('src.catalog')
local data={};local count=0
for _,source in ipairs({'data.wiki_hotspots','data.expanded_hotspots','data.aht_hotspots'}) do
    for map,entries in pairs(require(source)) do
        data[map]=data[map] or {};for id,record in pairs(entries) do data[map][id]=record end
    end
end
U.pending_locate=false;test_player=nil;test_members={}
for map,entries in pairs(data) do for id,record in pairs(entries) do
    N.go(test_state,'zone',map);opened_popup=nil
    local exit
    for _,e in ipairs(C.exits(map)) do if e.id==id then exit=e end end
    assert(exit)
    local pt=record.polygons[1][1]
    local ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    hover=true;mouse_x=ox+pt[1]*s;mouse_y=oy+pt[2]*s;mouse_clicked=true
    callbacks.d3d_present();mouse_clicked=false;click_at(mouse_x,mouse_y)
    if opened_popup then
        local found=false;for _,choice in ipairs(U.choices) do if choice.id==id then found=true end end
        assert(found,id)
    else assert(test_state.current.key==exit.target.map,id) end
    count=count+1
end end
opened_popup=nil;hover=false
-- Region names are artwork; closer zoom opens native zones.
local W=require('src.world').data
for _,filter in pairs(U.poi_filters) do filter[1]=false end
-- Location pips attach to zone labels only; no marker floats by a region title.
restore_people();N.go(test_state,'world');local view=test_state.current
view.initialized=true;view.world_legacy=nil;view.zoom=1;calls={};callbacks.d3d_present()
for _,call in ipairs(calls) do
    assert(not (call[1]=='AddCircleFilled' and call[4]==0xFF9DE6A5),'Player pip on region overview')
end
local S=require('src.world_selectors');local L=require('src.map_labels')
local node=S.node('zone-100');view.zoom=6;view.cx=(node.bounds[1]+node.bounds[3])/2
view.cy=(node.bounds[2]+node.bounds[4])/2;calls={};callbacks.d3d_present()
local ox,oy,scale=N.transform(view,0,0,viewport_w,viewport_h,W.width,W.height)
local bounds=S.bounds(node,scale,L.measure);local found=false
for _,call in ipairs(calls) do if call[1]=='AddCircleFilled' and call[4]==0xFF9DE6A5 then
    local pt=call[2]
    if math.abs(pt[1]-(ox+bounds[1]*scale-5))<.001 and
        math.abs(pt[2]-(oy+(bounds[2]+bounds[4])/2*scale))<.001 then found=true end
end end
assert(found,'Player pip missing from corrected zone label')
test_player=nil;test_members={}
for id,bounds in pairs(W.hotspots) do
    command('world');click_button='Fit';callbacks.d3d_present();click_button=nil
    local ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,W.width,W.height)
    click_at(ox+(bounds[1]+bounds[3])/2*s,oy+(bounds[2]+bounds[4])/2*s)
    assert(test_state.current.level=='world' and test_state.current.zoom==1 and not test_state.current.focus,id)
end
for _,node in ipairs(W.zones) do
    command('world');click_button='Fit';callbacks.d3d_present();click_button=nil
    local v=test_state.current;local b=node.bounds
    v.cx=(b[1]+b[3])/2;v.cy=(b[2]+b[4])/2;v.zoom=6
    callbacks.d3d_present();assert(U.world_lod>=4 and #active_assets<=16)
    click_at(viewport_w/2,viewport_h/2)
    assert(test_state.current.level=='zone' and test_state.current.key==node.maps[1],node.title)
    callbacks.d3d_present();assert(#active_assets==0)
end
for _,filter in pairs(U.poi_filters) do filter[1]=true end
asset_cache={};missing_art=true;command('world');click_button='Fit';callbacks.d3d_present();click_button=nil
assert(test_state.current.world_legacy and test_state.current.zoom_max==5 and #active_assets==0)
missing_art=false;select_label='Reload maps';opened_popup='##atlas-options';callbacks.d3d_present();select_label=nil;opened_popup=nil
assert(not test_state.current.world_legacy)
-- Outward navigation follows the current zone after a passage, independent of
-- the location previously visited on the world map.
local N=require('src.navigation');local C=require('src.catalog')
for _,key in ipairs(C.order) do
    N.go(test_state,'zone',key);callbacks.d3d_present()
    hover=true;wheel=-1;callbacks.d3d_present();wheel=0;hover=false;callbacks.d3d_present()
    local v=test_state.current;local b=require('src.world').zone_bounds(key)
    assert(v.level=='world' and math.abs(v.cx-(b[1]+b[3])/2)<.001 and math.abs(v.cy-(b[2]+b[4])/2)<.001,key)
    assert(v.zoom>=2.5,key)
end
local remembered=test_state.current;remembered.cx=3100;remembered.cy=3400;remembered.zoom=5
N.go(test_state,'zone','west');local zone=test_state.current
N.up(test_state);callbacks.d3d_present();assert(test_state.current.level=='world' and test_state.current.zoom==5)
N.back(test_state);assert(test_state.current==zone)
N.back(test_state);assert(test_state.current==remembered and remembered.cx==3100 and remembered.cy==3400)
restore_people()
command('ronfaure');callbacks.d3d_present()
local function group_counts(color)
    local count=0;for _,c in ipairs(calls) do if c[1]=='AddText' and c[3]==color then count=count+1 end end
    return count
end
calls={};callbacks.d3d_present();local party_counts=group_counts(0xFFF1C47C)
assert(party_counts>0 and group_counts(0xFFD4A8E4)>0)
U.party[1]=false;calls={};callbacks.d3d_present();assert(group_counts(0xFFF1C47C)==0)
U.alliance[1]=false;calls={};callbacks.d3d_present();assert(group_counts(0xFFD4A8E4)==0)
U.party[1]=true;U.alliance[1]=true
imported_areas_tested=count
""")
print(f'PASS: {lua.globals().imported_areas_tested} imported polygon clicks, passive region names, relative outward navigation, history and missing-art fallback')

with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=ADDON/'tests') as temp:
    lua.globals().editor_save_path=(Path(temp)/'exit-areas.json').as_posix()
    lua.execute(r"""
    local U=require('src.ui');local N=require('src.navigation');local C=require('src.catalog')
    local H=require('src.hotspots');local E=U.editor
    U.load_areas(editor_save_path);U.pending_locate=false;U.visible[1]=true
    test_player=nil;test_members={};N.go(test_state,'zone','fort');command('edit');callbacks.d3d_present()
    assert(E.active and test_state.current.key=='fort')
    local exit=C.exits('fort')[1];E.selected=exit.id
    click_button='Draw area';callbacks.d3d_present();click_button=nil;assert(E.tool=='draw')
    local ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    local cx,cy=test_state.current.cx,test_state.current.cy
    hover=true;mouse_x=ox+40*s;mouse_y=oy+50*s;mouse_clicked=true;mouse_down=true
    callbacks.d3d_present();mouse_clicked=false
    mouse_x=ox+100*s;mouse_y=oy+85*s;dragging=true;drag_dx=60*s;drag_dy=35*s
    callbacks.d3d_present()
    assert(test_state.current.cx==cx and test_state.current.cy==cy, 'Drawing an area panned the map')
    dragging=false;mouse_down=false;release=true;callbacks.d3d_present();release=false;hover=false
    local r=H.get(U.areas,'fort',exit)
    assert(math.abs(r[1]-40)<0.001 and math.abs(r[4]-85)<0.001 and U.areas.dirty)
    assert(test_state.current.key=='fort', 'Editing followed an exit')
    click_button='Save';callbacks.d3d_present();click_button=nil;assert(not U.areas.dirty)
    local loaded=H.new();assert(H.load(loaded,editor_save_path,C))
    assert(math.abs(H.get(loaded,'fort',exit)[1]-40)<0.001)
    click_button='Reset area';callbacks.d3d_present();click_button=nil
    assert(not (U.areas.areas.fort and U.areas.areas.fort[exit.id]))
    click_button='Undo';callbacks.d3d_present();click_button=nil
    assert(math.abs(H.get(U.areas,'fort',exit)[1]-40)<0.001)
    click_button='Done';callbacks.d3d_present();click_button=nil;assert(not E.active)
    -- The saved rectangle works after zoom/pan, independent of the old anchors.
    test_state.current.zoom=2;test_state.current.cx=100;test_state.current.cy=100
    ox,oy,s=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    mouse_x=ox+70*s;mouse_y=oy+65*s;hover=true;mouse_clicked=true
    callbacks.d3d_present();mouse_clicked=false;click_at(mouse_x,mouse_y)
    assert(test_state.current.key==exit.target.map and test_state.current.arrival.passage==exit.id)
    U.areas=H.new();U.message=nil;restore_people()
    """)
print('PASS: on-map area editor, drag/pan isolation, reset/undo, save/reload and zoomed custom-area travel')

lua.execute(r"""
local P=require('src.pois');local U=require('src.ui');local N=require('src.navigation')
U.pending_locate=false;U.editor.active=false;test_player=nil;test_members={}
for _,group in ipairs(P.groups) do
    command('world');callbacks.d3d_present()
    local v=test_state.current;v.cx=group.x;v.cy=group.y;v.zoom=6
    callbacks.d3d_present();click_at(viewport_w/2,viewport_h/2)
    if group.stops[1].map then assert(test_state.current.key==group.stops[1].map,group.id)
    else assert(opened_popup=='##atlas-poi',group.id);opened_popup=nil end
end
local count=0
for id,stop in pairs(P.stops) do if stop.map then
    P.visit(test_state,id);callbacks.d3d_present()
    click_at(viewport_w/2,viewport_h/2)
    assert(opened_popup=='##atlas-poi',id)
    if #P.links[id]>0 then
        local target=P.links[id][1].target
        select_label='To '..target.area..'##poi-to-'..target.id
        callbacks.d3d_present();select_label=nil;assert(not opened_popup)
        callbacks.d3d_present()
        if target.map then
            assert(test_state.current.key==target.map and test_state.current.arrival.poi==target.id,id)
        else
            local w=P.hubs[target.hub].world
            assert(test_state.current.level=='world' and test_state.current.cx==w[1] and test_state.current.cy==w[2],id)
        end
    else
        select_label='World map##poi-world-'..id
        callbacks.d3d_present();select_label=nil;assert(not opened_popup)
        callbacks.d3d_present()
        assert(test_state.current.level=='world',id)
    end
    count=count+1
end end
-- All markers are optional, including hit testing, without altering exits.
for _,filter in pairs(U.poi_filters) do filter[1]=false end
N.go(test_state,'zone','port_jeuno');calls={};hover=false;callbacks.d3d_present()
for _,c in ipairs(calls) do assert(c[1]~='AddCircle','Hidden POIs left icons behind') end
for _,filter in pairs(U.poi_filters) do filter[1]=true end
opened_popup=nil;hover=false;restore_people();poi_routes_tested=count
""")
print(f'PASS: all transport hubs, {lua.globals().poi_routes_tested} native boarding clicks, destination browsing and category filters')

lua.execute(r"""
local Q=require('src.conquest');local N=require('src.navigation');local U=require('src.ui')
assert(Q.owner('outpost-ronfaure').name=='Unknown')
local packet=string.rep('\0',0x66)
for region,raw in pairs({[1]=1,[2]=2,[3]=3,[4]=4,[15]=2,[16]=3,[19]=1}) do
    local index=0x1D+(region-1)*4+1
    packet=packet:sub(1,index-1)..string.char(raw)..packet:sub(index+1)
end
callbacks.packet_in({id=0x05E,data=packet})
assert(Q.owner('outpost-ronfaure').name=="San d'Oria")
assert(Q.owner('outpost-zulkheim').name=='Bastok')
assert(Q.owner('outpost-norvallen').name=='Windurst')
assert(Q.owner('outpost-gustaberg').name=='Beastmen')
assert(Q.owner('outpost-tavnazia').name=="San d'Oria")
assert(Q.owner('outpost-tulia').name=='Unknown')
local red=Q.nations[0].color
local r,g,b=bit.band(red,255),bit.band(bit.rshift(red,8),255),bit.band(bit.rshift(red,16),255)
assert(r>g*1.8 and r>b*1.8,'San d\'Oria flag is not a saturated red in ImGui ABGR')
assert(not Q.ingest('short') and Q.owner('outpost-ronfaure').name=="San d'Oria")
N.go(test_state,'world');test_state.current.zoom=6;U.pending_locate=false;test_player=nil
calls={};hover=false;callbacks.d3d_present()
local seen={}
for _,call in ipairs(calls) do if call[1]=='AddTriangleFilled' then seen[call[5]]=true end end
for _,nation in pairs(Q.nations) do assert(seen[nation.color],'Missing nation-colored outpost flag') end
local sent,scheduled={},{}
AshitaCore={GetPacketManager=function() return {AddOutgoingPacket=function(_,id,bytes) sent[#sent+1]={id,bytes} end} end}
ashita.tasks={once=function(seconds,fn) scheduled[#scheduled+1]={seconds,fn} end}
Q.start();assert(Q.owner('outpost-ronfaure').name=='Unknown' and scheduled[1][1]==1)
scheduled[1][2]();assert(sent[1][1]==0x05A and #sent[1][2]==4 and sent[1][2][1]==0)
Q.zoned();assert(Q.owner('outpost-ronfaure').name=='Unknown' and scheduled[2][1]==3)
scheduled[2][2]();assert(sent[2][1]==0x05A)
AshitaCore=nil;ashita.tasks=nil
restore_people()
""")
print('PASS: live Conquest owner decoding, nation-colored outpost flags and neutral fallback')


with tempfile.TemporaryDirectory(prefix='_poi_ui_tmp_',dir=ADDON/'tests') as temp:
    lua.globals().poi_save_path=(Path(temp)/'poi-corrections.json').as_posix()
    lua.execute(r"""
    local P=require('src.pois');local U=require('src.ui');local N=require('src.navigation')
    local D=require('src.poi_edits');local E=U.poi_editor;local W=require('src.world').data
    U.load_pois(poi_save_path);U.pending_locate=false;test_player=nil;test_members={}
    local marker=P.markers({level='zone',key='mhaura'},P.filters())[1]
    local id=marker.stops[1].id;P.visit(test_state,id);command('poi');callbacks.d3d_present()
    assert(E.active and not U.editor.active)
    local ox,oy,scale=N.transform(test_state.current,0,0,viewport_w,viewport_h,512,512)
    local cx,cy=test_state.current.cx,test_state.current.cy
    hover=true;mouse_x=ox+marker.x*scale;mouse_y=oy+marker.y*scale;mouse_clicked=true;mouse_down=true
    callbacks.d3d_present();mouse_clicked=false
    mouse_x=mouse_x+25*scale;mouse_y=mouse_y+15*scale;dragging=true;drag_dx=25*scale;drag_dy=15*scale
    callbacks.d3d_present();assert(test_state.current.cx==cx and test_state.current.cy==cy)
    dragging=false;mouse_down=false;release=true;callbacks.d3d_present();release=false;hover=false
    assert(test_state.current.key=='mhaura' and not opened_popup and P.edits.dirty)
    for _,stop in ipairs(marker.stops) do assert(math.abs(P.stops[stop.id].x-marker.x-25)<.001) end
    click_button='Undo POI';callbacks.d3d_present();click_button=nil;assert(not P.edits.dirty)
    E.selected='outpost-ronfaure'
    click_button='View world';callbacks.d3d_present();click_button=nil;callbacks.d3d_present()
    click_button='Place on map';callbacks.d3d_present();click_button=nil;assert(E.tool=='place')
    local wx,wy=4000,3000
    ox,oy,scale=N.transform(test_state.current,0,0,viewport_w,viewport_h,W.width,W.height)
    hover=true;mouse_x=ox+wx*scale;mouse_y=oy+wy*scale;mouse_clicked=true;mouse_down=true
    callbacks.d3d_present();mouse_clicked=false;mouse_down=false;release=true;callbacks.d3d_present();release=false;hover=false
    assert(test_state.current.level=='world' and P.hubs['outpost-ronfaure'].world[1]==wx)
    click_button='Hide POI';callbacks.d3d_present();click_button=nil;assert(P.stops['outpost-ronfaure'].hidden)
    click_button='Show POI';callbacks.d3d_present();click_button=nil;assert(not P.stops['outpost-ronfaure'].hidden)
    click_button='Copy corrections';callbacks.d3d_present();click_button=nil
    assert(not P.edits.dirty and require('json').decode(clipboard).changes.world['outpost-ronfaure'].x==wx)
    P.edits=D.new();U.load_pois(poi_save_path);assert(P.hubs['outpost-ronfaure'].world[1]==wx)
    click_button='Done editing POIs';callbacks.d3d_present();click_button=nil;assert(not E.active)
    P.edits=D.new();P.refresh();E.cancel();U.message=nil;restore_people()
    """)
print('PASS: POI editor gestures, shared docks, world placement, pan/travel isolation, hide/show, copy and reload')


with tempfile.TemporaryDirectory(prefix='_selector_ui_tmp_',dir=ADDON/'tests') as temp:
    lua.globals().selector_save_path=(Path(temp)/'world-selectors.json').as_posix()
    lua.execute(r"""
    local U=require('src.ui');local N=require('src.navigation');local S=require('src.world_selectors')
    local E=U.selector_editor;local W=require('src.world').data
    U.load_selectors(selector_save_path);U.pending_locate=false;test_player=nil;test_members={}
    N.go(test_state,'zone','west');command('selectors');callbacks.d3d_present()
    assert(E.active and not U.poi_editor.active and not U.editor.active and test_state.current.level=='world')
    assert(E.selected=='zone-100')
    -- Draw well away from the original printed banner to prove real hit testing uses the override.
    click_button='Fit';callbacks.d3d_present();click_button=nil
    click_button='Draw selector';callbacks.d3d_present();click_button=nil;assert(E.tool=='draw')
    local v=test_state.current;local cx,cy=v.cx,v.cy
    local ox,oy,scale=N.transform(v,0,0,viewport_w,viewport_h,W.width,W.height)
    hover=true;mouse_x=ox+7500*scale;mouse_y=oy+7200*scale;mouse_clicked=true;mouse_down=true
    callbacks.d3d_present();mouse_clicked=false
    mouse_x=ox+7900*scale;mouse_y=oy+7400*scale;dragging=true;drag_dx=400*scale;drag_dy=200*scale
    callbacks.d3d_present();assert(v.cx==cx and v.cy==cy)
    dragging=false;mouse_down=false;release=true;callbacks.d3d_present();release=false;hover=false
    assert(test_state.current==v and not opened_popup and S.store.dirty)
    assert(S.node('zone-100').bounds[1]==7500 and S.node('zone-100').bounds[4]==7400)
    -- Normal blank-space panning still works in selector mode.
    hover=true;mouse_x=ox+9000*scale;mouse_y=oy+7000*scale;mouse_clicked=true;mouse_down=true
    callbacks.d3d_present();mouse_clicked=false;dragging=true;drag_dx=20;drag_dy=10
    callbacks.d3d_present();assert(v.cx~=cx and v.cy~=cy)
    dragging=false;mouse_down=false;release=true;callbacks.d3d_present();release=false;hover=false
    click_button='Copy selectors';callbacks.d3d_present();click_button=nil
    assert(not S.store.dirty and require('json').decode(clipboard).selectors['zone-100'][1]==7500)
    S.set('zone-100',nil);assert(S.load(selector_save_path));assert(S.node('zone-100').bounds[1]==7500)
    click_button='Done with selectors';callbacks.d3d_present();click_button=nil;assert(not E.active)
    v.zoom=6;v.cx=7700;v.cy=7300
    hover=true;mouse_x=viewport_w/2;mouse_y=viewport_h/2;mouse_clicked=true
    callbacks.d3d_present();mouse_clicked=false
    click_at(viewport_w/2,viewport_h/2)
    assert(test_state.current.level=='zone' and test_state.current.key=='west')
    S.store={changes={},saved={},undo={},dirty=false};S.refresh();E.cancel();U.message=nil;restore_people()
    """)
print('PASS: world selector UI, drawing/pan isolation, copied/reloaded bounds and corrected zone navigation')


lua.execute(r"""
local U=require('src.ui');local N=require('src.navigation');local S=require('src.world_selectors')
local P=require('src.pois');local L=require('src.map_labels');local W=require('src.world').data
U.pending_locate=false;test_player=nil;test_members={}
for _,f in pairs(U.poi_filters) do f[1]=false end
-- Larger type, wrapping and the measured click area agree.
L.set_scale(L.reference_scale)
local w,h=L.measure('Navukgo Execution Chamber');assert(w<=L.max_width and h>=L.size)
local previous=0;local measured={}
for _,zoom in ipairs({2.5,4,6,12,32}) do
    N.go(test_state,'world');local v=test_state.current;local node=S.node('zone-50');local b=node.bounds
    v.initialized=true;v.layout='world';v.world_legacy=nil;v.zoom=zoom;v.cx=(b[1]+b[3])/2;v.cy=(b[2]+b[4])/2
    callbacks.d3d_present()
    assert(L.pixel_size>=previous and L.pixel_size>=L.min_size and L.pixel_size<=L.max_size)
    previous=L.pixel_size;measured[#measured+1]=L.pixel_size
    local ox,oy,scale=N.transform(v,0,0,viewport_w,viewport_h,W.width,W.height)
    local r=S.bounds(node,scale,L.measure);local tw,th=L.measure(node.title)
    assert(math.abs((r[3]-r[1])*scale-tw-12)<.001 and math.abs((r[4]-r[2])*scale-th-8)<.001)
    mouse_x=ox+r[3]*scale-2;mouse_y=viewport_h/2;hover=true;mouse_clicked=true
    callbacks.d3d_present();mouse_clicked=false;click_at(mouse_x,mouse_y)
    assert(test_state.current.key==node.maps[1],'Scaled label edge was not clickable')
end
assert(measured[1]<measured[2] and measured[2]<measured[3] and measured[4]==measured[5])
assert(measured[1]==L.min_size and measured[5]==L.max_size)
local buckets=0;for _ in pairs(L.cache) do buckets=buckets+1 end;assert(buckets<=8)
assert(font_loads==1 and #font_stack==0,'Font atlas mutated during drawing or font stack leaked')
-- Independent printed-artwork reproductions from the Gemini review now work.
for _,sample in ipairs({{7060,4205,'the_boyahda_tree'},{5600,1845,'the_shrine_of_ru_avitau'},{5430,5145,'outer_horutoto_ruins_f1'}}) do
    N.go(test_state,'world');local view=test_state.current
    view.world_legacy=nil;view.initialized=true;view.layout='world';view.zoom=6;view.cx=sample[1];view.cy=sample[2]
    mouse_clicked=true;hover=true;mouse_x=viewport_w/2;mouse_y=viewport_h/2;callbacks.d3d_present();mouse_clicked=false
    click_at(viewport_w/2,viewport_h/2)
    assert(test_state.current.level=='zone',sample[3])
    local target=require('src.catalog').maps[test_state.current.key]
    local expected=sample[3]=='the_boyahda_tree' and 153 or sample[3]=='the_shrine_of_ru_avitau' and 178 or 194
    assert(target.zone==expected,sample[3])
end
-- Purgonorgo has its own world banner and a bidirectional Manaclipper connection.
N.go(test_state,'world');local v=test_state.current;v.world_legacy=nil;v.initialized=true;v.layout='world';v.zoom=6;v.cx=6850;v.cy=5304
mouse_clicked=true;hover=true;mouse_x=viewport_w/2;mouse_y=viewport_h/2;callbacks.d3d_present();mouse_clicked=false
click_at(viewport_w/2,viewport_h/2);assert(test_state.current.key=='bibiki_bay_f2')
local marker=P.markers({level='zone',key='bibiki_bay_f2'},P.filters())[1]
local link=P.links[marker.stops[1].id][1]
assert(link.target.map=='bibiki_bay_f1' and link.route.id=='manaclipper-bibiki-purgonorgo')
for _,f in pairs(U.poi_filters) do f[1]=true end
restore_people();hover=false;opened_popup=nil
""")
print('PASS: zoom-scaled measured serif labels, one-time font load, user banner corrections and Purgonorgo world/boat links')

parser=argparse.ArgumentParser();parser.add_argument('--preview-dir',type=Path)
output=parser.parse_args().preview_dir
if output:
    output.mkdir(parents=True,exist_ok=True)
    raw=LuaRuntime(encoding=None,unpack_returned_tuples=True)
    raw.execute(b"package.path = ... .. '/?.lua;' .. package.path",ADDON.as_posix().encode())
    wrap=raw.eval(b"require('src.dat_image').wrap")
    ffxi=ROOT/'SquareEnix/FINAL FANTASY XI'
    ft=(ffxi/'FTABLE.DAT').read_bytes();vt=(ffxi/'VTABLE.DAT').read_bytes()
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13)
    texture_cache={}
    flags={}
    def point(t):return tuple(float(t[i]) for i in (1,2))
    def color(value):return tuple((int(value)>>shift)&255 for shift in (0,8,16,24))
    def get_texture(dat):
        if dat in texture_cache:return texture_cache[dat]
        if isinstance(dat,str):
            texture_cache[dat]=Image.open(ADDON/dat).convert('RGBA')
            return texture_cache[dat]
        packed=struct.unpack_from('<H',ft,int(dat)*2)[0];rom=vt[int(dat)]
        path=Path('ROM' if rom==1 else f'ROM{rom}')/str(packed>>7)/f'{packed&127}.DAT'
        chosen=ffxi/path
        for overlay in ['horizonoverrides','remapster','xiview','ffxivision']:
            candidate=ROOT/'polplugins/DATs'/overlay/path
            if candidate.exists():chosen=candidate;flags[dat]=overlay=='remapster';break
        encoded,_,_=wrap(chosen.read_bytes())
        texture_cache[dat]=Image.open(io.BytesIO(encoded)).convert('RGBA')
        return texture_cache[dat]
    for _,definition in lua.eval("require('src.catalog').maps").items():
        if definition['dat'] is not None:get_texture(definition['dat'])
    lua.globals().preview_flags=lua.table_from(flags)
    for name,setup in [
        ('conquest',"command('world');click_button='Fit';callbacks.d3d_present();click_button=nil"),
        ('outpost-colors',"require('src.conquest').owners={[1]=0,[2]=1,[3]=2,[4]=3};for _,filter in pairs(require('src.ui').poi_filters) do filter[1]=false end;require('src.ui').poi_filters.outpost[1]=true;command('world');callbacks.d3d_present();test_state.current.zoom=2.5;test_state.current.cx=3600;test_state.current.cy=4300"),
        ('besieged',"for _,filter in pairs(require('src.ui').poi_filters) do filter[1]=true end;command('besieged')"),
        ('besieged-labels-wide',"command('besieged');callbacks.d3d_present();test_state.current.zoom=2.5"),
        ('besieged-labels-close',"command('besieged');callbacks.d3d_present();test_state.current.zoom=6"),
        ('besieged-detail',"command('besieged');callbacks.d3d_present();test_state.current.zoom=4"),
        ('bibiki',"require('src.navigation').go(test_state,'zone','bibiki_bay_f1')"),
        ('purgonorgo',"require('src.navigation').go(test_state,'zone','bibiki_bay_f2')"),
        ('whitegate',"require('src.navigation').go(test_state,'zone','aht_urhgan_whitegate_f0')"),
        ('talacca',"require('src.navigation').go(test_state,'zone','talacca_cove')"),
        ('ronfaure',"command('ronfaure')"),
        ('zulkheim',"command('zulkheim')"),
        ('norvallen',"command('norvallen')"),
        ('fauregandi',"command('fauregandi')"),
        ('gustaberg',"command('gustaberg')"),
        ('derfland',"command('derfland')"),
        ('valdeaunia',"command('valdeaunia')"),
        ('vollbow',"command('vollbow')"),
        ('world-detail',"command('world');click_button='Fit';callbacks.d3d_present();click_button=nil;calls={};test_state.current.zoom=5;test_state.current.cx=3100;test_state.current.cy=3400"),
        ('poi-jeuno',"require('src.navigation').go(test_state,'zone','port_jeuno')"),
        ('poi-selbina',"require('src.navigation').go(test_state,'zone','selbina')"),
        ('poi-sandoria',"require('src.navigation').go(test_state,'zone','port')"),
        ('fort',"require('src.navigation').go(test_state,'zone','fort')"),
        ('exit-editor',"require('src.navigation').go(test_state,'zone','fort');command('edit')"),
        ('arrival',"require('src.navigation').go(test_state,'zone','west');require('src.navigation').travel(test_state,require('src.catalog').exits('west')[1])"),
        ('party',"command('here');require('src.ui').names[1]=true")]:
        lua.execute("calls={};require('src.ui').message=nil;require('src.ui').editor.active=false;"+setup+';callbacks.d3d_present();for i=1,18 do calls={};callbacks.d3d_present() end')
        canvas=Image.new('RGBA',(1100,760),(19,31,25,255));clips=[(0,0,1100,760)]
        for _,c in lua.globals().calls.items():
            op=c[1]
            if op=='PushClipRect':
                a,b=point(c[2]),point(c[3]);old=clips[-1];clips.append((max(old[0],a[0]),max(old[1],a[1]),min(old[2],b[0]),min(old[3],b[1])));continue
            if op=='PopClipRect':clips.pop();continue
            layer=Image.new('RGBA',canvas.size);d=ImageDraw.Draw(layer)
            if op in ['AddRect','AddRectFilled']:
                bounds=[point(c[2]),point(c[3])];radius=float(c[5] or 0)
                if op=='AddRectFilled':d.rounded_rectangle(bounds,radius=radius,fill=color(c[4]))
                else:d.rounded_rectangle(bounds,radius=radius,outline=color(c[4]),width=max(1,round(float(c[7] or 1))))
            elif op=='AddRectFilledMultiColor':
                a,b=point(c[2]),point(c[3]);im=Image.new('RGBA',(2,2));im.putdata([color(c[i]) for i in (4,5,7,6)])
                im=im.resize((round(b[0]-a[0]),round(b[1]-a[1])),Image.Resampling.BILINEAR);layer.alpha_composite(im,(round(a[0]),round(a[1])))
            elif op=='AddLine':d.line([point(c[2]),point(c[3])],fill=color(c[4]),width=max(1,round(float(c[5] or 1))))
            elif op=='AddBezierCubic':
                a,p,q,b=[point(c[i]) for i in (2,3,4,5)];pts=[]
                for i in range(49):
                    t=i/48;u=1-t;pts.append(tuple(u**3*a[j]+3*u*u*t*p[j]+3*u*t*t*q[j]+t**3*b[j] for j in (0,1)))
                d.line(pts,fill=color(c[6]),width=max(1,round(float(c[7]))))
            elif op in ['AddCircle','AddCircleFilled']:
                x,y=point(c[2]);r=float(c[3]);bounds=[x-r,y-r,x+r,y+r]
                if op=='AddCircle':d.ellipse(bounds,outline=color(c[4]),width=max(1,round(float(c[6] or 1))))
                else:d.ellipse(bounds,fill=color(c[4]))
            elif op=='AddTriangleFilled':d.polygon([point(c[i]) for i in (2,3,4)],fill=color(c[5]))
            elif op=='AddText':d.multiline_text(point(c[2]),c[4],font=label_preview_font(c['font_size']) if c['font_family']!='default' else font,fill=color(c[3]),spacing=0)
            elif op=='AddImage':
                x,y=point(c[3]);x2,y2=point(c[4]);im=get_texture(c[2]);u1,v1=point(c[5]);u2,v2=point(c[6])
                im=im.crop((u1*im.width,v1*im.height,u2*im.width,v2*im.height)).resize((max(1,round(x2)-round(x)),max(1,round(y2)-round(y))),Image.Resampling.LANCZOS)
                rgba=color(c[7]);im=ImageChops.multiply(im,Image.new('RGBA',im.size,rgba));layer.alpha_composite(im,(round(x),round(y)))
            box=tuple(round(v) for v in clips[-1])
            if box[2]>box[0] and box[3]>box[1]:canvas.alpha_composite(layer.crop(box),box[:2])
        d=ImageDraw.Draw(canvas);d.rectangle([0,741,1100,760],fill=(12,22,17,255))
        d.text((8,742),'ATLAS 0.8.7 / Offline canvas preview - live client validation pending',font=font,fill='#b1c2b4')
        canvas.convert('RGB').save(output/f'atlas-{name}.png')
    print(f'Canvas previews: {output}')
