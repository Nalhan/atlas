local imgui=require('imgui')
local C=require('src.catalog')
local N=require('src.navigation')
local client=require('src.client')
local H=require('src.hotspots')
local editor=require('src.exit_editor')
local World=require('src.world')
local POI=require('src.pois')
local U={state=N.new(),visible={true},pending_locate=true,party={true},alliance={true},names={false},search={''}}
U.areas=H.new();U.editor=editor
U.poi_filters=POI.filters()
local palette={gold=0xFF8EC6E3,ink=0xFF14231C,cream=0xFFE7EBD9,muted=0xFF9BADA1,
    party=0xFFF1C47C,alliance=0xFFD4A8E4,you=0xFF9DE6A5,arrival=0xFFF2BC73}
local world={dat=5312}
local dragged=false

local function tip(text)
    imgui.BeginTooltip();imgui.TextUnformatted(text);imgui.EndTooltip()
end
local function hot_tip(text) if imgui.IsItemHovered() then tip(text) end end
local function hand() imgui.SetMouseCursor(ImGuiMouseCursor_Hand) end
local function text(draw,x,y,value,color,centered)
    local w,h=imgui.CalcTextSize(value)
    draw:AddText({centered and x-w/2 or x,y-h/2},color or palette.cream,value)
end
local function pill(draw,x,y,value,color)
    local w,h=imgui.CalcTextSize(value)
    draw:AddRectFilled({x-w/2-9,y-h/2-5},{x+w/2+9,y+h/2+5},0xF01B2D23,4)
    draw:AddRect({x-w/2-9,y-h/2-5},{x+w/2+9,y+h/2+5},0x77678C7E,4)
    text(draw,x,y,value,color,true)
end
local function reset_view()
    local v=U.state.current;v.zoom=1
    v.focus=nil
    v.cx=v.level=='world' and not v.world_legacy and World.data.width/2 or 256
    v.cy=v.level=='world' and not v.world_legacy and World.data.height/2 or 256
end
local function toast(value) U.message=value;U.message_at=os.clock() end
function U.load_areas(path)
    U.area_path=path or (AshitaCore and AshitaCore:GetInstallPath()..'config/addons/atlas/exit-areas.json')
    local ok,err=H.load(U.areas,U.area_path,C)
    if not ok then toast(err) end
end
function U.save_areas()
    if not U.areas.dirty then return true end
    local ok,err=H.save(U.areas,U.area_path,C)
    toast(ok and 'Exit areas saved' or err);return ok
end
local function locate(p,quiet)
    if not p then if not quiet then toast('Position unavailable') end;return false end
    local key=C.find_player_map(p.zone,p.floor)
    if not key then if not quiet then toast('This area is outside the atlas') end;return false end
    local x,y=client.position(C.maps[key],p)
    N.go(U.state,'zone',key)
    if x then U.state.current.cx=x;U.state.current.cy=y;U.state.current.zoom=1.6 end
    U.message=nil
    return true
end
function U.locate()
    U.pending_locate=false
    return locate(client.player(),false)
end
function U.open(level,key)
    U.visible[1]=true;U.message=nil
    U.pending_locate=level==nil
    if level then N.go(U.state,level,key) end
end
function U.edit_exits()
    if editor.active then
        if U.save_areas() then editor.active=false;editor.cancel() end
        return
    end
    U.visible[1]=true;U.pending_locate=false
    if U.state.current.level~='zone' and not U.locate() then return end
    editor.active=true;editor.cancel()
end
local function go(level,key) N.go(U.state,level,key) end
local function control(label,action,hint,disabled)
    imgui.BeginDisabled(disabled or false)
    if imgui.Button(label) then action() end
    imgui.EndDisabled()
    if hint then hot_tip(hint) end
end
local function permitted(member)
    return member.group=='party' and U.party[1] or member.group=='alliance' and U.alliance[1]
end
local function outline(draw,x,y,size,color)
    local gap=4
    for _,sx in ipairs({-1,1}) do
        for _,sy in ipairs({-1,1}) do
            draw:AddLine({x+sx*size,y+sy*size},{x+sx*gap,y+sy*size},color,2)
            draw:AddLine({x+sx*size,y+sy*size},{x+sx*size,y+sy*gap},color,2)
        end
    end
end
local function area_outline(draw,r,ox,oy,s)
    local l,t,bx,by=ox+r[1]*s,oy+r[2]*s,ox+r[3]*s,oy+r[4]*s
    local n=math.min(10,(bx-l)/3,(by-t)/3)
    for _,corner in ipairs({{l,t,1,1},{bx,t,-1,1},{bx,by,-1,-1},{l,by,1,-1}}) do
        local x,y,dx,dy=unpack(corner)
        draw:AddLine({x,y},{x+dx*n,y},palette.gold,1.5)
        draw:AddLine({x,y},{x,y+dy*n},palette.gold,1.5)
    end
end
local function actor(draw,x,y,heading,color,self)
    local a=heading+math.pi/2
    local function point(dx,dy)
        return {x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a)}
    end
    local r=self and 8 or 6
    draw:AddCircleFilled({x,y},r+2,0xEE192A22)
    draw:AddCircle({x,y},r+2,color,20,1)
    draw:AddTriangleFilled(point(0,-r),point(-r*0.65,r*0.6),point(r*0.65,r*0.6),color)
end

local function open_choices(choices)
    if #choices==1 then N.travel(U.state,choices[1]);return end
    U.choices=choices;U.popup_pending=true
end
local function choices_popup()
    if U.popup_pending then imgui.OpenPopup('##atlas-passages');U.popup_pending=false end
    if imgui.BeginPopup('##atlas-passages') then
        for i,exit in ipairs(U.choices or {}) do
            local name=C.maps[exit.source.map].name..' > '..C.maps[exit.target.map].name
            if exit.target.component and exit.target.component~='main' then
                name=name..' ['..exit.target.component:gsub('_',' ')..']'
            end
            if exit.source.label then name=name..' / '..exit.source.label end
            if imgui.Selectable(name..'##passage-'..i,false) then
                N.travel(U.state,exit);imgui.CloseCurrentPopup()
            end
        end
        imgui.EndPopup()
    end
end
local function poi_popup()
    if U.poi_pending then imgui.OpenPopup('##atlas-poi');U.poi_pending=false end
    if imgui.BeginPopup('##atlas-poi') then
        local marker=U.poi_selection
        imgui.TextUnformatted(marker.title);imgui.Separator()
        for _,stop in ipairs(marker.stops) do
            for _,link in ipairs(POI.links[stop.id]) do
                local destination=link.target
                if imgui.Selectable('To '..destination.area..'##poi-to-'..destination.id,false) then
                    POI.visit(U.state,destination.id);imgui.CloseCurrentPopup()
                end
                hot_tip(link.route.requirement..(destination.map and '' or '\nWorld map location'))
                imgui.TextUnformatted(link.route.requirement)
            end
        end
        imgui.EndPopup()
    end
end
local function poi_icon(draw,x,y,kind,hot)
    local color=POI.types[kind].color
    draw:AddCircleFilled({x,y},12,0xEE14231C)
    draw:AddCircle({x,y},10,hot and palette.cream or color,24,hot and 2 or 1.5)
    if kind=='boat' then
        draw:AddLine({x-7,y+2},{x-3,y+6},color,1.8)
        draw:AddLine({x-3,y+6},{x+3,y+6},color,1.8)
        draw:AddLine({x+3,y+6},{x+7,y+2},color,1.8)
        draw:AddLine({x-7,y+2},{x+7,y+2},color,1.8)
        draw:AddLine({x,y-7},{x,y+1},color,1.5)
        draw:AddTriangleFilled({x+1,y-6},{x+6,y},{x+1,y},color)
    elseif kind=='airship' then
        draw:AddRectFilled({x-7,y-5},{x+7,y+1},color,3)
        draw:AddLine({x-3,y+2},{x-2,y+5},color,1.3)
        draw:AddLine({x+3,y+2},{x+2,y+5},color,1.3)
        draw:AddLine({x-3,y+5},{x+3,y+5},color,2)
    else
        draw:AddCircleFilled({x,y},3,color)
    end
end
local function poi_layer(draw,ox,oy,s,hover,mx,my,click)
    if editor.active then return false end
    local view=U.state.current;local markers=POI.markers(view,U.poi_filters)
    local hot,nearest
    for _,marker in ipairs(markers) do
        local d=(mx-ox-marker.x*s)^2+(my-oy-marker.y*s)^2
        if hover and d<=14^2 and (not nearest or d<nearest) then hot=marker;nearest=d end
    end
    if hot and view.level=='world' then
        for _,stop in ipairs(hot.stops) do for _,link in ipairs(POI.links[stop.id]) do
            local hub=POI.hubs[link.target.hub];local ax,ay=ox+hot.x*s,oy+hot.y*s
            local bx,by=ox+hub.world[1]*s,oy+hub.world[2]*s
            local bend=math.min(90,math.abs(bx-ax)*.15)
            draw:AddBezierCubic({ax,ay},{ax+(bx-ax)*.3,ay-bend},{ax+(bx-ax)*.7,by-bend},{bx,by},
                bit.band(POI.types[hot.category].color,0x00FFFFFF)+0xBB000000,1.5,32)
        end end
    end
    for _,marker in ipairs(markers) do
        local x,y=ox+marker.x*s,oy+marker.y*s
        if view.poi_focus then for _,stop in ipairs(marker.stops) do
            if stop.id==view.poi_focus then draw:AddCircle({x,y},15,palette.arrival,24,1.5);break end
        end end
        poi_icon(draw,x,y,marker.category,marker==hot)
        if #marker.stops>1 then
            draw:AddCircleFilled({x+9,y-9},6,0xFF14231C)
            text(draw,x+9,y-9,tostring(#marker.stops),palette.cream,true)
        end
    end
    if not hot then return false end
    hand()
    local lines={hot.title}
    for _,stop in ipairs(hot.stops) do for _,link in ipairs(POI.links[stop.id]) do
        lines[#lines+1]='To '..link.target.area..' / '..link.route.requirement
    end end
    tip(table.concat(lines,'\n'))
    if click then
        local stop=hot.stops[1]
        if view.level=='world' and stop.map then
            if #hot.stops==1 then POI.visit(U.state,stop.id) else go('zone',stop.map) end
        else U.poi_selection=hot;U.poi_pending=true end
    end
    return true
end
local function world_map(draw,ox,oy,s,hover,mx,my,click,player,members)
    local view=U.state.current;local legacy=view.world_legacy
    if legacy then
        local texture=client.texture(world)
        if texture and texture.id then draw:AddImage(texture.id,{ox,oy},{ox+512*s,oy+512*s},{0,0},{1,1},0xFFFFFFFF) end
    else
        for _,tile in ipairs(U.world_pages or {}) do
            local page=tile.page
            draw:AddImage(tile.id,{ox+page.x*s,oy+page.y*s},{ox+(page.x+page.w)*s,oy+(page.y+page.h)*s},{0,0},{1,1},0xFFFFFFFF)
        end
    end
    if not legacy and view.zoom>=2.5 then
        for _,node in ipairs(World.data.zones) do
            if node.supplementary then
                local b=node.bounds;local x,y=ox+(b[1]+b[3])/2*s,oy+(b[2]+b[4])/2*s
                text(draw,x+1,y+1,node.title,0xFF14231C,true)
                text(draw,x,y,node.title,palette.cream,true)
            end
        end
        for _,node in ipairs(World.data.zones) do
            local b=node.bounds;local l,r=ox+b[1]*s,ox+b[3]*s;local y=oy+(b[2]+b[4])/2*s
            local counts={party=0,alliance=0}
            for _,key in ipairs(node.maps) do
                if player and C.maps[key].zone==player.zone then draw:AddCircleFilled({l-5,y},4,palette.you);break end
            end
            for _,member in ipairs(members) do
                if permitted(member) then for _,key in ipairs(node.maps) do
                    if C.maps[key].zone==member.zone then counts[member.group]=counts[member.group]+1;break end
                end end
            end
            for _,group in ipairs({'party','alliance'}) do
                if counts[group]>0 then
                    draw:AddCircleFilled({r+8,y},3,palette[group]);text(draw,r+14,y,tostring(counts[group]),palette[group]);r=r+24
                end
            end
        end
        if poi_layer(draw,ox,oy,s,hover,mx,my,click) then return end
        for _,node in ipairs(World.data.zones) do
            local b=node.bounds;local x1,y1,x2,y2=ox+b[1]*s,oy+b[2]*s,ox+b[3]*s,oy+b[4]*s
            if hover and mx>=x1 and mx<=x2 and my>=y1 and my<=y2 then
                draw:AddRect({x1,y1},{x2,y2},palette.gold,3,0,1.5);hand()
                local lines={node.title}
                for _,member in ipairs(members) do
                    if permitted(member) then for _,key in ipairs(node.maps) do
                        if C.maps[key].zone==member.zone then lines[#lines+1]=member.name..' / '..member.group;break end
                    end end
                end
                tip(table.concat(lines,'\n'))
                if click then
                    local key=node.maps[1]
                    if player then for _,candidate in ipairs(node.maps) do
                        if C.maps[candidate].zone==player.zone and C.maps[candidate].floor==player.floor then key=candidate end
                    end end
                    go('zone',key)
                end
                return
            end
        end
    end
    if view.zoom<2.5 then poi_layer(draw,ox,oy,s,hover,mx,my,click) end
    if not legacy then
        if player and view.zoom<2.5 then
            local key=C.find_player_map(player.zone,player.floor)
            local b=key and World.data.hotspots[C.maps[key].region]
            if b then draw:AddCircleFilled({ox+(b[1]+b[3])/2*s,oy+b[4]*s-5},4,palette.you) end
        end
    end
end

local function zone_map(draw,ox,oy,s,hover,mx,my,click,player,members)
    local view=U.state.current;local def=C.maps[view.key]
    local texture=client.texture(def)
    if texture and texture.id then
        draw:AddImage(texture.id,{ox,oy},{ox+512*s,oy+512*s},{0,0},{1,1},0xFFFFFFFF)
    else
        text(draw,ox+256*s,oy+145*s,def.name,palette.gold,true)
        text(draw,ox+256*s,oy+165*s,def.dat and 'Map unavailable' or 'No charted map',palette.muted,true)
    end
    local poi_hot=poi_layer(draw,ox,oy,s,hover,mx,my,click)
    local exits=C.exits(view.key)
    local hits=hover and not poi_hot and H.hits(U.areas,view.key,exits,(mx-ox)/s,(my-oy)/s) or {}
    local nearest=hits[1]
    -- The map's own mouths, arrows and printed letters are the controls.
    -- Only uncharted/unavailable maps need plain text to expose their exits.
    if not (texture and texture.id) then
        for _,exit in ipairs(exits) do
            text(draw,ox+exit.source.x*s,oy+exit.source.y*s,
                exit.source.label or exit.target.label or C.maps[exit.target.map].name,palette.gold,true)
        end
    end
    if editor.active then editor.draw(draw,U.areas,view.key,exits,ox,oy,s)
    elseif nearest then area_outline(draw,H.get(U.areas,view.key,nearest),ox,oy,s) end
    if view.arrival then
        outline(draw,ox+view.arrival.x*s,oy+view.arrival.y*s,21,palette.arrival)
    end
    local hovered_actor
    for _,member in ipairs(members) do
        if permitted(member) then
            local px,py=client.position(def,member)
            if px and px>=0 and px<=512 and py>=0 and py<=512 then
                local x,y=ox+px*s,oy+py*s
                actor(draw,x,y,member.heading,palette[member.group])
                if U.names[1] then pill(draw,x,y-19,member.name,palette[member.group]) end
                if hover and (mx-x)^2+(my-y)^2<12^2 then hovered_actor=member end
            end
        end
    end
    local px,py=client.position(def,player)
    if px and px>=0 and px<=512 and py>=0 and py<=512 then
        local x,y=ox+px*s,oy+py*s
        actor(draw,x,y,player.heading,palette.you,true)
        if U.names[1] then pill(draw,x,y-20,player.name,palette.you) end
        if hover and (mx-x)^2+(my-y)^2<12^2 then hovered_actor={name=player.name,group='You'} end
    end
    if editor.active or poi_hot then return end
    if hovered_actor then tip(hovered_actor.name..' / '..hovered_actor.group) end
    if nearest then
        local exit=nearest
        hand()
        local value=C.maps[exit.target.map].name
        if exit.target.component and exit.target.component~='main' then
            value=value..'\n'..exit.target.component:gsub('_',' ')
        end
        if exit.source.label then value=value..'\n'..exit.source.label end
        if exit.note then value=value..'\n'..exit.note end
        tip(value)
        if click then
            open_choices(hits)
        end
    end
end

local function canvas(player,members)
    local v=U.state.current
    local x,y=imgui.GetCursorScreenPos();local w,h=imgui.GetContentRegionAvail()
    w,h=math.max(1,w),math.max(1,h)
    local rw,rh=512,512
    if v.level=='world' then
        rw,rh=v.world_legacy and 512 or World.data.width,v.world_legacy and 512 or World.data.height
        v.zoom_max=v.world_legacy and 5 or World.data.maximum_zoom
        local layout=v.world_legacy and 'conquest' or 'world'
        if not v.initialized or v.layout~=layout then
            v.cx=rw/2;v.cy=rh/2;v.initialized=true;v.layout=layout
            if v.focus and not v.world_legacy then
                local b=v.focus;v.cx=(b[1]+b[3])/2;v.cy=(b[2]+b[4])/2
                v.zoom=v.return_zoom or math.max(1,math.min(v.zoom_max,.9*math.min(w/(b[3]-b[1]),h/(b[4]-b[2]))/math.min(w/rw,h/rh)))
            end
        end
    else
        client.keep_assets({},24)
    end
    imgui.InvisibleButton('##atlas-canvas',{w,h})
    local hover=imgui.IsItemHovered();local mx,my=imgui.GetMousePos()
    if imgui.IsMouseClicked(0) then dragged=false;U.drag_dx=0;U.drag_dy=0 end
    if imgui.IsMouseDragging(0) then dragged=true end
    local click=hover and imgui.IsMouseReleased(0) and not dragged
    if hover and not editor.drag and imgui.GetIO().MouseWheel~=0 then
        local factor=1.2^imgui.GetIO().MouseWheel
        if v.level=='zone' and not editor.active and v.zoom*factor<1 then N.up(U.state);return end
        N.zoom_at(v,factor,mx,my,x,y,w,h,rw,rh)
    end
    if v.level=='world' and hover and (imgui.GetIO().MouseWheel~=0 or imgui.IsMouseDragging(0)) then
        U.world_busy_until=os.clock()+0.12
    end
    local ox,oy,s=N.transform(v,x,y,w,h,rw,rh)
    local editing=editor.active and v.level=='zone'
    local consumed=editing and editor.pointer(U.areas,v.key,C.exits(v.key),(mx-ox)/s,(my-oy)/s,s,
        hover,imgui.IsMouseClicked(0),imgui.IsMouseDown(0),imgui.IsMouseReleased(0))
    if not consumed and imgui.IsItemActive() and imgui.IsMouseDragging(0) then
        local dx,dy=imgui.GetMouseDragDelta(0)
        v.cx=v.cx-(dx-(U.drag_dx or 0))/s;v.cy=v.cy-(dy-(U.drag_dy or 0))/s
        U.drag_dx,U.drag_dy=dx,dy
        ox,oy,s=N.transform(v,x,y,w,h,rw,rh)
    end
    if v.level=='world' and not v.world_legacy then
        U.world_pages,U.world_lod=World.prepare(client,ox,oy,s,x,y,w,h,os.clock()<(U.world_busy_until or 0))
        if not U.world_pages then
            v.world_legacy=true;v.layout='conquest';v.cx=256;v.cy=256;v.zoom=1;v.zoom_max=5;rw,rh=512,512
            client.keep_assets({})
            ox,oy,s=N.transform(v,x,y,w,h,rw,rh)
        end
    end
    local draw=imgui.GetWindowDrawList()
    draw:PushClipRect({x,y},{x+w,y+h},true)
    draw:AddRectFilledMultiColor({x,y},{x+w,y+h},0xFF2B3022,0xFF20271C,0xFF181F16,0xFF222B1E)
    if v.level=='world' then world_map(draw,ox,oy,s,hover,mx,my,click,player,members)
    else zone_map(draw,ox,oy,s,hover,mx,my,click,player,members) end
    if U.message and os.clock()-(U.message_at or 0)<4 then pill(draw,x+w/2,y+22,U.message,palette.gold) end
    draw:PopClipRect()
    if hover and imgui.IsMouseReleased(1) then
        if editing then editor.cancel()
        elseif v.level=='world' then
            if v.zoom<=1 then reset_view() else N.zoom_at(v,.5,mx,my,x,y,w,h,rw,rh) end
        else N.up(U.state) end
    end
    if hover and imgui.IsMouseClicked(3) then N.back(U.state) end
    if hover and imgui.IsMouseClicked(4) then N.forward(U.state) end
    choices_popup()
    poi_popup()
end

local function toolbar()
    local v=U.state.current
    control('<',function() N.back(U.state) end,'Back',#U.state.back==0);imgui.SameLine()
    control('>',function() N.forward(U.state) end,'Forward',#U.state.forward==0);imgui.SameLine()
    control('World',function() if v.level~='world' then N.up(U.state) end end);imgui.SameLine()
    if v.level~='world' then
        imgui.TextUnformatted('/');imgui.SameLine()
    end
    imgui.SetNextItemWidth(245)
    if imgui.BeginCombo('##atlas-area',v.level=='zone' and C.maps[v.key].name or 'Areas') then
        imgui.SetNextItemWidth(-1);imgui.InputTextWithHint('##atlas-find','Find an area',U.search,128)
        local query=U.search[1]:lower()
        for _,key in ipairs(C.order) do
            local def=C.maps[key]
            if query=='' or def.name:lower():find(query,1,true) then
                if imgui.Selectable(def.name..'##area-'..key,v.key==key) then go('zone',key) end
            end
        end
        imgui.EndCombo()
    end
    imgui.SameLine();control('Locate',U.locate,'Center on you')
    imgui.SameLine();control('Fit',reset_view,'Fit map')
    imgui.SameLine()
    if imgui.Button('...') then imgui.OpenPopup('##atlas-options') end
    if imgui.BeginPopup('##atlas-options') then
        imgui.Checkbox('Names',U.names)
        imgui.TextUnformatted('Points of interest')
        for _,category in ipairs(POI.categories) do imgui.Checkbox(category.label,U.poi_filters[category.id]) end
        if imgui.Selectable('Edit exit areas',editor.active) then U.edit_exits();imgui.CloseCurrentPopup() end
        if imgui.Selectable('Reload maps',false) then
            client.clear();client.init()
            if v.world_legacy then v.world_legacy=nil;v.initialized=false end
        end
        imgui.Separator();imgui.TextUnformatted('Wheel: zoom   Drag: pan\nRight click: zoom out / world')
        imgui.EndPopup()
    end
    v=U.state.current
    if v.level=='zone' then
        local siblings=C.siblings(v.key)
        if #siblings>1 then
            for i,key in ipairs(siblings) do
                if i>1 then imgui.SameLine() end
                local active=key==v.key
                if active then imgui.PushStyleColor(ImGuiCol_Button,0xFF45634E) end
                if imgui.Button(C.maps[key].tab..'##floor-'..key) and not active then go('zone',key) end
                if active then imgui.PopStyleColor() end
            end
            imgui.SameLine();imgui.TextUnformatted('  |  ');imgui.SameLine()
        end
    end
    imgui.Checkbox('Party',U.party);imgui.SameLine();imgui.Checkbox('Alliance',U.alliance)
    if editor.active and v.level=='zone' then
        local exits=C.exits(v.key);local selected=editor.prepare(v.key,exits)
        imgui.Separator();imgui.TextUnformatted('Edit exits');imgui.SameLine()
        imgui.SetNextItemWidth(280)
        local function label(exit)
            return C.maps[exit.target.map].name..(exit.source.code and ' / '..exit.source.code or '')
                ..(exit.source.label and ' / '..exit.source.label or '')
        end
        if imgui.BeginCombo('##atlas-edit-exit',selected and label(selected) or 'No exits') then
            for _,exit in ipairs(exits) do
                if imgui.Selectable(label(exit)..'##edit-'..exit.id,exit.id==editor.selected) then
                    editor.selected=exit.id;editor.cancel()
                end
            end
            imgui.EndCombo()
        end
        imgui.SameLine();control('Draw area',function() editor.cancel();editor.tool='draw' end,'Drag a box around the map graphic',not selected)
        imgui.SameLine();control('Undo',function() editor.cancel();H.undo(U.areas) end,nil,#U.areas.undo==0)
        imgui.SameLine();control('Reset area',function()
            editor.cancel();H.set(U.areas,v.key,editor.selected,nil)
        end,'Restore this exit\'s default area',not selected or not (U.areas.areas[v.key] and U.areas.areas[v.key][editor.selected]))
        imgui.SameLine();control('Save',U.save_areas,nil,not U.areas.dirty)
        imgui.SameLine();control('Done',U.edit_exits,'Save changes and leave edit mode')
        imgui.TextUnformatted(editor.tool=='draw' and 'Drag around the exit graphic. Right click cancels.'
            or 'Select an exit; drag its box to move, or a corner to resize.'..(U.areas.dirty and '   Unsaved' or ''))
    end
    imgui.Separator()
end
function U.draw()
    if not U.visible[1] then return end
    local player=client.player()
    -- Wait for position data when opened during zoning. Explicit destination
    -- commands bypass this default, and browsing stays free once it resolves.
    if U.pending_locate and player and player.floor~=nil then
        U.pending_locate=false
        if not locate(player,true) then N.go(U.state,'world') end
    end
    imgui.SetNextWindowSize({1150,850},ImGuiCond_FirstUseEver)
    imgui.SetNextWindowSizeConstraints({960,680},{2400,1800})
    local flags=bit.bor(ImGuiWindowFlags_NoScrollbar,ImGuiWindowFlags_NoScrollWithMouse)
    imgui.PushStyleColor(ImGuiCol_WindowBg,0xFF292C21)
    imgui.PushStyleColor(ImGuiCol_Button,0xFF3A4B36)
    imgui.PushStyleColor(ImGuiCol_ButtonHovered,0xFF526B4B)
    imgui.PushStyleColor(ImGuiCol_ButtonActive,0xFF607E58)
    imgui.PushStyleColor(ImGuiCol_FrameBg,0xFF303D2B)
    imgui.PushStyleColor(ImGuiCol_PopupBg,0xFF252F21)
    if imgui.Begin('Atlas',U.visible,flags) then
        toolbar()
        local members=client.members(player)
        imgui.BeginChild('##atlas-map',{0,0},ImGuiChildFlags_None,flags)
        canvas(player,members);imgui.EndChild()
    end
    imgui.End();imgui.PopStyleColor(6)
end
return U
