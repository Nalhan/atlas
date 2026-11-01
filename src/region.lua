-- A focused Ronfaure atlas board. Floors share one thumbnail; city districts
-- share a hub. Only this region has hand-placed artwork and route bends.
local R={width=1200,height=940,nodes={},order={},by_map={}}
local function node(key,title,x,y,w,h,maps,crop)
    local n={key=key,title=title,x=x,y=y,w=w,h=h,maps=maps,
        crop=crop or {0.25,0.30,0.75,0.78}}
    R.nodes[key]=n; R.order[#R.order+1]=key
    for _,map in ipairs(maps) do R.by_map[map]=key end
end
node('fort','Fort Ghelsba',130,160,190,140,{'fort'})
node('grotto','Yughott Grotto',375,130,210,145,{'grotto1','grotto2'},{0.23,0.27,0.8,0.73})
node('horlais','Horlais Peak',630,100,180,110,{'horlais'})
node('outpost','Ghelsba Outpost',145,430,215,175,{'outpost','outpost2'})
node('city',"San d'Oria",655,300,215,150,{'north','south','port','chateau'},{0.15,0.20,0.92,0.82})
node('oubliette','Bostaunieux Oubliette',985,170,245,155,{'oubliette1','oubliette2','oubliette3'},{0.25,0.34,0.72,0.66})
node('west','West Ronfaure',445,505,295,280,{'west'},{0.28,0.22,0.70,0.83})
node('east','East Ronfaure',790,545,295,280,{'east'},{0.32,0.20,0.77,0.79})
node('ranguemont','Ranguemont Pass',1085,420,200,140,{'ranguemont'},{0.23,0.26,0.76,0.82})
node('tomb',"King Ranperre's Tomb",1070,720,225,155,{'tomb1','tomb2'},{0.28,0.24,0.75,0.70})
node('latheine','La Theine Plateau',405,800,225,135,{'latheine'},{0.18,0.26,0.85,0.82})
node('jugner','Jugner Forest',735,820,210,120,{'jugner'},{0.28,0.25,0.80,0.82})

function R.routes_for(board,catalog)
    local result,by_pair={},{}
    for _,p in ipairs(catalog.passages) do
        local a,b=board.by_map[p.a.map],board.by_map[p.b.map]
        if a and b and a~=b then
            local key=a<b and a..':'..b or b..':'..a
            local route=by_pair[key]
            if not route then route={a=a,b=b,passages={}}; by_pair[key]=route;result[#result+1]=route end
            route.passages[#route.passages+1]=p
        end
    end
    return result
end
function R.routes(catalog) return R.routes_for(R,catalog) end
function R.thumbnail_uv(hub,aspect)
    -- Expand the crop to the card's aspect instead of stretching zone geometry.
    local c=hub.crop
    local cx,cy=(c[1]+c[3])/2,(c[2]+c[4])/2
    local w=math.min(1,math.max(c[3]-c[1],(c[4]-c[2])*aspect))
    local h=math.min(1,w/aspect)
    w=math.min(1,h*aspect)
    local x=math.max(0,math.min(1-w,cx-w/2))
    local y=math.max(0,math.min(1-h,cy-h/2))
    return {x,y},{x+w,y+h}
end
function R.count_members(hub,members)
    local counts={party=0,alliance=0}
    for _,member in ipairs(members) do
        for _,key in ipairs(hub.maps) do
            if member.zone==require('src.catalog').maps[key].zone then
                counts[member.group]=counts[member.group]+1;break
            end
        end
    end
    return counts
end
return R
