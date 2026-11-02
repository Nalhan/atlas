local S=require('src.world_selectors')
local E={active=false,tool='select'}
function E.cancel() E.drag=nil;E.tool='select' end
function E.selected_node()
    local node=S.node(E.selected) or S.data.zones[1];E.selected=S.id(node);return node
end
function E.rect(node,scale,measure)
    if E.drag and E.drag.id==S.id(node) then return E.drag.preview end
    return S.bounds(node,scale,measure)
end
local function contains(r,x,y) return x>=r[1] and x<=r[3] and y>=r[2] and y<=r[4] end
local function corners(r) return {{r[1],r[2]},{r[3],r[2]},{r[3],r[4]},{r[1],r[4]}} end
local function rect(x1,y1,x2,y2)
    return {math.max(0,math.min(S.data.width,math.min(x1,x2))),math.max(0,math.min(S.data.height,math.min(y1,y2))),
        math.max(0,math.min(S.data.width,math.max(x1,x2))),math.max(0,math.min(S.data.height,math.max(y1,y2)))}
end
function E.pointer(x,y,scale,measure,hover,pressed,down,released)
    if pressed and hover then
        local node=E.selected_node();local r=S.bounds(node,scale,measure);local kind,corner
        if E.tool=='draw' then kind='draw'
        else
            for i,p in ipairs(corners(r)) do
                if math.abs(x-p[1])*scale<=8 and math.abs(y-p[2])*scale<=8 then kind='resize';corner=i;break end
            end
            if not kind and contains(r,x,y) then kind='move' end
            if not kind then
                local best
                for _,candidate in ipairs(S.data.zones) do
                    local b=S.bounds(candidate,scale,measure)
                    if contains(b,x,y) then
                        local distance=(x-(b[1]+b[3])/2)^2+(y-(b[2]+b[4])/2)^2
                        if not best or distance<best then node=candidate;r=b;best=distance;kind='move' end
                    end
                end
            end
        end
        if kind then E.selected=S.id(node);E.drag={id=E.selected,kind=kind,corner=corner,start={x,y},original=r,preview=r} end
    end
    local d=E.drag;if not d then return false end
    if down or released then
        local dx,dy=x-d.start[1],y-d.start[2];local r=d.original
        if d.kind=='draw' then d.preview=rect(d.start[1],d.start[2],x,y)
        elseif d.kind=='move' then
            dx=math.max(-r[1],math.min(S.data.width-r[3],dx));dy=math.max(-r[2],math.min(S.data.height-r[4],dy))
            d.preview={r[1]+dx,r[2]+dy,r[3]+dx,r[4]+dy}
        else
            local opposite={3,4,1,2};local p=corners(r)[opposite[d.corner]];d.preview=rect(p[1],p[2],x,y)
        end
        if released then
            if hover and (dx*dx+dy*dy)*scale*scale>=9 then
                local rounded={};for i,v in ipairs(d.preview) do rounded[i]=math.floor(v*1000+.5)/1000 end
                S.set(d.id,rounded)
            end
            E.cancel()
        end
    elseif not pressed then E.cancel() end
    return true
end
function E.draw(draw,ox,oy,scale,measure)
    E.selected_node()
    for _,node in ipairs(S.data.zones) do
        local r=E.rect(node,scale,measure);local selected=S.id(node)==E.selected
        local a,b={ox+r[1]*scale,oy+r[2]*scale},{ox+r[3]*scale,oy+r[4]*scale}
        draw:AddRectFilled(a,b,selected and 0x2244D9FF or 0x0E9DD8F4,2)
        draw:AddRect(a,b,selected and 0xFF8EC6E3 or 0x889BADA1,2,0,selected and 2 or 1)
        if selected then
            for _,p in ipairs(corners({a[1],a[2],b[1],b[2]})) do draw:AddRectFilled({p[1]-4,p[2]-4},{p[1]+4,p[2]+4},0xFF8EC6E3) end
            draw:AddText({a[1],a[2]-18},0xFF8EC6E3,node.title)
        end
    end
end
return E
