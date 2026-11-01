-- Category-driven points and transport links stay separate from walking exits.
local data=require('data.pois')
local P={categories=data.categories,types={},stops={},routes=data.routes,hubs=data.hubs,groups={},by_map={},links={}}
for _,category in ipairs(P.categories) do P.types[category.id]=category end
local groups={}
for _,stop in ipairs(data.stops) do
    P.stops[stop.id]=stop;P.links[stop.id]={}
    if stop.map then
        P.by_map[stop.map]=P.by_map[stop.map] or {};P.by_map[stop.map][#P.by_map[stop.map]+1]=stop
    end
    local key=stop.hub..'/'..stop.category
    if not groups[key] then
        local hub=data.hubs[stop.hub]
        groups[key]={id=key,category=stop.category,title=hub.title,x=hub.world[1],y=hub.world[2],stops={}}
        P.groups[#P.groups+1]=groups[key]
    end
    table.insert(groups[key].stops,stop)
end
for _,route in ipairs(data.routes) do
    table.insert(P.links[route.a],{route=route,target=P.stops[route.b]})
    table.insert(P.links[route.b],{route=route,target=P.stops[route.a]})
end
function P.filters()
    local result={};for _,category in ipairs(P.categories) do result[category.id]={true} end;return result
end
function P.markers(view,filters)
    local markers={}
    for _,item in ipairs(view.level=='world' and not view.world_legacy and P.groups or P.by_map[view.key] or {}) do
        if filters[item.category] and filters[item.category][1] then
            markers[#markers+1]=item.stops and item or {id=item.id,title=item.title,category=item.category,x=item.x,y=item.y,stops={item}}
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
