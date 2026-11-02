-- Reviewed baseline plus the separately generated deterministic source extension.
local data=require('data.catalog')
local extra=require('data.expansion')
local C={maps={},order={},passages={}}
local ids={}
for _,source in ipairs({data,extra,require('data.aht_urhgan')}) do
    for _,def in ipairs(source.maps) do
        assert(not C.maps[def.key],'Duplicate map key: '..def.key)
        C.maps[def.key]=def;C.order[#C.order+1]=def.key
    end
    for _,passage in ipairs(source.passages) do
        assert(not ids[passage.id],'Duplicate passage ID: '..passage.id)
        ids[passage.id]=true;C.passages[#C.passages+1]=passage
    end
end

-- Short labels belong in tabs and transient menus, not in a permanent sidebar.
local tabs={outpost='Outside',outpost2='Caves',grotto1='Lower',grotto2='Upper',
    tomb1='Map 1',tomb2='Map 2',oubliette1='Prison',oubliette2='Upper tunnels',oubliette3='Lower tunnels',
    north='North',south='South',port='Port',chateau='Chateau'}
for key,def in pairs(C.maps) do def.tab=tabs[key] or def.tab or def.name end
function C.siblings(key)
    local result={}
    local zone=C.maps[key].zone
    local function city(id)
        if id>=230 and id<=233 then return 'sandoria' end
        if id>=234 and id<=237 then return 'bastok' end
        if id>=238 and id<=241 then return 'windurst' end
        if id>=243 and id<=246 then return 'jeuno' end
    end
    for _,k in ipairs(C.order) do
        if C.maps[k].zone==zone or (city(zone) and city(C.maps[k].zone)==city(zone)) then
            result[#result+1]=k
        end
    end
    return result
end

function C.exits(key)
    local result = {}
    for _, p in ipairs(C.passages) do
        if p.a.map == key then
            result[#result+1] = { id=p.id, source=p.a, target=p.b, note=p.note, one_way=p.one_way }
        elseif p.b.map == key and not p.one_way then
            result[#result+1] = { id=p.id, source=p.b, target=p.a, note=p.note }
        end
    end
    return result
end

function C.find_player_map(zone, floor)
    for _, key in ipairs(C.order) do
        local m = C.maps[key]
        if not m.reference_only and m.zone == zone and (m.floor == floor or m.floor==nil) then return key end
    end
end
return C
