-- Category-driven points and transport links stay separate from walking exits.
local base=require('data.pois')
local edits=require('src.poi_edits')
local C=require('src.catalog')
local data=base
local P={categories=data.categories,types={},stops={},routes=data.routes,hubs=data.hubs,groups={},by_map={},links={}}
P.base=base;P.edits=edits.new()
function P.refresh()
    data=edits.apply(base,P.edits.changes,C)
    P.categories=data.categories;P.hubs=data.hubs;P.routes=data.routes
    P.types={};P.stops={};P.groups={};P.by_map={};P.links={}
    for _,category in ipairs(P.categories) do P.types[category.id]=category end
    local groups={}
    local docks={}
    for _,stop in ipairs(data.stops) do
        P.stops[stop.id]=stop;P.links[stop.id]={}
        if stop.map then
            local dock=stop.map..'/'..stop.category..'/'..stop.x..'/'..stop.y
            if not docks[dock] then
                docks[dock]={id=dock,title=stop.title,category=stop.category,x=stop.x,y=stop.y,stops={}}
                P.by_map[stop.map]=P.by_map[stop.map] or {};table.insert(P.by_map[stop.map],docks[dock])
            end
            table.insert(docks[dock].stops,stop)
            if #docks[dock].stops>1 then docks[dock].title=stop.area..' / '..P.types[stop.category].label end
        end
        local key=stop.hub..'/'..stop.category
        if not groups[key] then
            local hub=data.hubs[stop.hub]
            groups[key]={id=key,hub=stop.hub,category=stop.category,title=hub.title,x=hub.world[1],y=hub.world[2],stops={}}
            P.groups[#P.groups+1]=groups[key]
        end
        table.insert(groups[key].stops,stop)
    end
    for _,route in ipairs(data.routes) do
        if not P.stops[route.a].hidden and not P.stops[route.b].hidden then
        table.insert(P.links[route.a],{route=route,target=P.stops[route.b]})
        table.insert(P.links[route.b],{route=route,target=P.stops[route.a]})
        end
    end
end
P.refresh()
function P.filters()
    local result={};for _,category in ipairs(P.categories) do result[category.id]={true} end;return result
end
function P.markers(view,filters,editing)
    local markers={}
    for _,item in ipairs(view.level=='world' and not view.world_legacy and P.groups or P.by_map[view.key] or {}) do
        if editing or (filters[item.category] and filters[item.category][1]) then
            local stops={}
            for _,stop in ipairs(item.stops) do if editing or not stop.hidden then stops[#stops+1]=stop end end
            if #stops>0 then
                local marker={id=item.id,hub=item.hub,title=item.title,category=item.category,x=item.x,y=item.y,stops=stops}
                markers[#markers+1]=marker
            end
        end
    end
    return markers
end
function P.visit(state,id)
    local stop=P.stops[id];local N=require('src.navigation')
    if stop.map then
        N.go(state,'zone',stop.map,{x=stop.x,y=stop.y,poi=id})
    else
        local w=P.hubs[stop.hub].world
        N.go(state,'world');state.current.world_legacy=nil;state.current.initialized=false
        state.current.focus={w[1]-900,w[2]-700,w[1]+900,w[2]+700};state.current.return_zoom=nil
        state.current.poi_focus=id
    end
end
return P
