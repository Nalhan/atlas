local N = {}
function N.new()
    return { current={level='world', zoom=1, cx=256, cy=256}, back={}, forward={} }
end
function N.go(state, level, key, anchor)
    if state.current.level=='world' then
        state.overview={};for k,v in pairs(state.current) do state.overview[k]=v end
    end
    state.back[#state.back+1] = state.current
    if #state.back > 64 then table.remove(state.back,1) end
    state.forward = {}
    -- Older area commands are camera shortcuts on the single world canvas.
    local focus=level=='region' and require('src.world').data.regions[key or 'ronfaure'].bounds
    if level=='region' then level='world' end
    if level=='world' and not focus and state.overview then
        state.current={};for k,v in pairs(state.overview) do state.current[k]=v end
        return
    end
    local region
    if level=='zone' then region=require('src.catalog').maps[key].region or 'ronfaure' end
    state.current = { level=level, key=key, region=region, zoom=anchor and 1.8 or 1,
        cx=anchor and (anchor.focus_x or anchor.x) or 256,
        cy=anchor and (anchor.focus_y or anchor.y) or 256, arrival=anchor,focus=focus }
end
function N.travel(state, exit)
    N.go(state,'zone',exit.target.map,{x=exit.target.x,y=exit.target.y,
        focus_x=exit.target.arrival_x,focus_y=exit.target.arrival_y,
        from=exit.source.map, passage=exit.id})
end
function N.back(state)
    if #state.back == 0 then return end
    state.forward[#state.forward+1] = state.current
    state.current = table.remove(state.back)
end
function N.forward(state)
    if #state.forward == 0 then return end
    state.back[#state.back+1] = state.current
    state.current = table.remove(state.forward)
end
function N.up(state)
    if state.current.level == 'zone' then
        local key=state.current.key
        local zoom=state.overview and state.overview.zoom
        N.go(state,'region',state.current.region or 'ronfaure')
        state.current.focus=require('src.world').zone_bounds(key)
        state.current.return_zoom=zoom and zoom>=2.5 and zoom or nil
    end
end
-- Fit a reference-space point to a viewport. Deliberately allow empty margins at
-- arrivals so an entrance close to the map edge can still be centered exactly.
function N.transform(view,x,y,w,h,rw,rh)
    local scale=math.min(w/rw,h/rh)*view.zoom
    return x+w/2-view.cx*scale, y+h/2-view.cy*scale, scale
end
function N.zoom_at(view, factor, mx, my, x, y, w, h, rw, rh)
    local ox,oy,s=N.transform(view,x,y,w,h,rw,rh)
    local px,py=(mx-ox)/s,(my-oy)/s
    view.zoom=math.max(1,math.min(view.zoom_max or 5,view.zoom*factor))
    local ns=math.min(w/rw,h/rh)*view.zoom
    view.cx=px-(mx-x-w/2)/ns
    view.cy=py-(my-y-h/2)/ns
end
return N
