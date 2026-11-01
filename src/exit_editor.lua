local H=require('src.hotspots')
local E={active=false,tool='select'}
function E.prepare(map,exits)
    if E.map~=map then E.map=map;E.selected=nil;E.drag=nil;E.tool='select' end
    local selected
    for _,exit in ipairs(exits) do if exit.id==E.selected then selected=exit end end
    selected=selected or exits[1];E.selected=selected and selected.id
    return selected
end
function E.cancel() E.drag=nil;E.tool='select' end
function E.area(store,map,exit)
    if E.drag and E.drag.map==map and E.drag.id==exit.id then return E.drag.preview end
    return H.get(store,map,exit)
end
function E.pointer(store,map,exits,x,y,scale,hover,pressed,down,released)
    local selected=E.prepare(map,exits)
    if pressed and hover and selected then
        local r=H.get(store,map,selected);local kind,corner
        if E.tool=='draw' then kind='draw'
        else
            for i,p in ipairs({{r[1],r[2]},{r[3],r[2]},{r[3],r[4]},{r[1],r[4]}}) do
                if math.abs(x-p[1])*scale<=8 and math.abs(y-p[2])*scale<=8 then kind='resize';corner=i;break end
            end
            if not kind then
                local hits=H.hits(store,map,exits,x,y)
                if hits[1] then selected=hits[1];E.selected=selected.id;r=H.get(store,map,selected);kind='move' end
            end
        end
        if kind then E.drag={kind=kind,corner=corner,map=map,id=selected.id,start={x,y},original=r,preview=r} end
    end
    local drag=E.drag
    if not drag then return false end
    if down or released then
        local r=drag.original;local dx,dy=x-drag.start[1],y-drag.start[2]
        if drag.kind=='draw' then drag.preview=H.rect(drag.start[1],drag.start[2],x,y)
        elseif drag.kind=='move' then
            dx=math.max(-r[1],math.min(512-r[3],dx));dy=math.max(-r[2],math.min(512-r[4],dy))
            drag.preview={r[1]+dx,r[2]+dy,r[3]+dx,r[4]+dy}
        else
            local opposite={ {r[3],r[4]}, {r[1],r[4]}, {r[1],r[2]}, {r[3],r[2]} }
            local p=opposite[drag.corner];drag.preview=H.rect(p[1],p[2],x,y)
        end
        if released then
            if (dx*dx+dy*dy)*scale*scale>=16 and H.valid(drag.preview) then H.set(store,map,drag.id,drag.preview) end
            E.cancel()
        end
    elseif not pressed then E.cancel() end -- release outside the canvas / lost focus
    return true
end
function E.draw(draw,store,map,exits,ox,oy,scale)
    E.prepare(map,exits)
    for _,exit in ipairs(exits) do
        local r=E.area(store,map,exit);local selected=exit.id==E.selected
        local a,b={ox+r[1]*scale,oy+r[2]*scale},{ox+r[3]*scale,oy+r[4]*scale}
        draw:AddRectFilled(a,b,selected and 0x2244D9FF or 0x0E9DD8F4,2)
        draw:AddRect(a,b,selected and 0xFF8EC6E3 or 0x889BADA1,2,0,selected and 2 or 1)
        if selected then
            for _,p in ipairs({a,{b[1],a[2]},b,{a[1],b[2]}}) do
                draw:AddRectFilled({p[1]-4,p[2]-4},{p[1]+4,p[2]+4},0xFF8EC6E3)
            end
        end
    end
end
return E
