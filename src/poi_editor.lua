local P=require('src.pois')
local edits=require('src.poi_edits')
local W=require('src.world').data
local E={active=false,tool='select'}
function E.cancel() E.drag=nil;E.tool='select' end
function E.selected_stop() return P.stops[E.selected] or P.stops[P.base.stops[1].id] end
function E.position(marker)
    local d=E.drag
    if d and d.marker.id==marker.id then return d.x,d.y end
    return marker.x,marker.y
end
function E.place(view,stops,x,y,hub)
    local changes=edits.clone(P.edits.changes)
    local function round(n) return math.floor(n*1000+.5)/1000 end
    if view.level=='world' then
        if view.world_legacy then return false end
        changes.world[hub or stops[1].hub]={x=round(x),y=round(y)}
    else
        for _,stop in ipairs(stops) do
            local p=changes.stops[stop.id] or {};changes.stops[stop.id]=p
            p.map=view.key;p.x=round(x);p.y=round(y)
        end
    end
    local changed=edits.set(P.edits,changes);P.refresh();return changed
end
function E.pointer(view,x,y,scale,hover,pressed,down,released)
    if E.view~=view then E.cancel();E.view=view end
    if view.world_legacy then return false end
    if pressed and hover then
        local selected=E.selected_stop();local marker,nearest
        if E.tool=='place' then
            marker={id='placing',hub=selected.hub,stops={selected},x=x,y=y}
        else
            for _,candidate in ipairs(P.markers(view,{},true)) do
                local distance=((x-candidate.x)^2+(y-candidate.y)^2)*scale*scale
                if distance<=18^2 and (not nearest or distance<nearest) then marker=candidate;nearest=distance end
            end
        end
        if marker then
            E.selected=marker.stops[1].id
            E.drag={marker=marker,start={x,y},x=marker.x,y=marker.y,place=E.tool=='place'}
        end
    end
    local d=E.drag;if not d then return false end
    if down or released then
        local maxx,maxy=view.level=='world' and W.width or 512,view.level=='world' and W.height or 512
        local dx,dy=x-d.start[1],y-d.start[2]
        d.x=math.max(0,math.min(maxx,d.marker.x+dx));d.y=math.max(0,math.min(maxy,d.marker.y+dy))
        if released then
            if hover and (d.place or (dx*dx+dy*dy)*scale*scale>=9) then E.place(view,d.marker.stops,d.x,d.y,d.marker.hub) end
            E.cancel()
        end
    elseif not pressed then E.cancel() end
    return true
end
function E.hide()
    local stop=E.selected_stop();local changes=edits.clone(P.edits.changes)
    local p=changes.stops[stop.id] or {};changes.stops[stop.id]=p;p.hidden=not stop.hidden
    edits.set(P.edits,changes);P.refresh();E.cancel()
end
function E.reset(view)
    local changes=edits.clone(P.edits.changes);local stop=E.selected_stop()
    if view.level=='world' then changes.world[stop.hub]=nil else changes.stops[stop.id]=nil end
    edits.set(P.edits,changes);P.refresh();E.cancel()
end
return E
