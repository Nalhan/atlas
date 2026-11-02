-- User-authored click areas stay separate from generated passage coordinates.
local H={}
local imported={}
for _,source in ipairs({require('data.wiki_hotspots'),require('data.expanded_hotspots'),require('data.aht_hotspots')}) do
    for map,entries in pairs(source) do
        imported[map]=imported[map] or {}
        for id,entry in pairs(entries) do imported[map][id]=entry end
    end
end
local function clone(value)
    if type(value)~='table' then return value end
    local result={};for k,v in pairs(value) do result[k]=clone(v) end;return result
end
local function finite(n) return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge end
function H.rect(x1,y1,x2,y2)
    return {math.max(0,math.min(512,math.min(x1,x2))),math.max(0,math.min(512,math.min(y1,y2))),
        math.max(0,math.min(512,math.max(x1,x2))),math.max(0,math.min(512,math.max(y1,y2)))}
end
function H.valid(r)
    if type(r)~='table' or #r~=4 then return false end
    for _,n in ipairs(r) do if not finite(n) or n<0 or n>512 then return false end end
    return r[3]-r[1]>=4 and r[4]-r[2]>=4
end
function H.contains(r,x,y) return x>=r[1] and y>=r[2] and x<=r[3] and y<=r[4] end
function H.default(exit)
    local e=exit.source;local bx,by=e.badge_x or e.x,e.badge_y or e.y
    return H.rect(math.min(e.x,bx)-24,math.min(e.y,by)-16,math.max(e.x,bx)+24,math.max(e.y,by)+16)
end
function H.new() return {areas={},saved={},undo={},dirty=false} end
local function published(map,exit)
    local data=imported[map] and imported[map][exit.id]
    if data and exit.target and data.target_map==exit.target.map then return data end
end
function H.get(store,map,exit)
    local manual=store.areas[map] and store.areas[map][exit.id]
    if manual then return manual end
    local r=H.default(exit);local data=published(map,exit)
    if data then for _,poly in ipairs(data.polygons) do for _,p in ipairs(poly) do
        r[1]=math.min(r[1],p[1]);r[2]=math.min(r[2],p[2]);r[3]=math.max(r[3],p[1]);r[4]=math.max(r[4],p[2])
    end end end
    return r
end
function H.in_polygon(poly,x,y)
    local inside=false
    for i,a in ipairs(poly) do
        local b=poly[i%#poly+1]
        local dx,dy=b[1]-a[1],b[2]-a[2]
        local cross=(x-a[1])*dy-(y-a[2])*dx
        if math.abs(cross)<0.00001 and x>=math.min(a[1],b[1])-0.00001 and x<=math.max(a[1],b[1])+0.00001
            and y>=math.min(a[2],b[2])-0.00001 and y<=math.max(a[2],b[2])+0.00001 then return true end
        if (a[2]>y)~=(b[2]>y) and x<(b[1]-a[1])*(y-a[2])/(b[2]-a[2])+a[1] then inside=not inside end
    end
    return inside
end
local function signature(areas)
    local rows={}
    for map,entries in pairs(areas) do for id,r in pairs(entries) do
        rows[#rows+1]=map..'/'..id..':'..table.concat(r,',')
    end end
    table.sort(rows);return table.concat(rows,';')
end
local function dirty(store) store.dirty=signature(store.areas)~=signature(store.saved) end
function H.set(store,map,id,rect)
    if rect and not H.valid(rect) then return false end
    local old=store.areas[map] and store.areas[map][id]
    if (not old and not rect) or (old and rect and table.concat(old,',')==table.concat(rect,',')) then return false end
    store.undo[#store.undo+1]={map=map,id=id,rect=clone(old)}
    if #store.undo>100 then table.remove(store.undo,1) end
    store.areas[map]=store.areas[map] or {};store.areas[map][id]=clone(rect)
    if not next(store.areas[map]) then store.areas[map]=nil end
    dirty(store);return true
end
function H.undo(store)
    local change=table.remove(store.undo);if not change then return end
    store.areas[change.map]=store.areas[change.map] or {}
    store.areas[change.map][change.id]=change.rect
    if not next(store.areas[change.map]) then store.areas[change.map]=nil end
    dirty(store)
end
function H.hits(store,map,exits,x,y)
    local hits={}
    for _,exit in ipairs(exits) do
        local manual=store.areas[map] and store.areas[map][exit.id]
        local hit=H.contains(manual or H.default(exit),x,y)
        local data=not manual and published(map,exit)
        if data then for _,poly in ipairs(data.polygons) do
            if H.in_polygon(poly,x,y) then hit=true;break end
        end end
        if hit then hits[#hits+1]=exit end
    end
    local function distance(exit)
        local e=exit.source
        return math.min((x-e.x)^2+(y-e.y)^2,(x-(e.badge_x or e.x))^2+(y-(e.badge_y or e.y))^2)
    end
    table.sort(hits,function(a,b)
        local da,db=distance(a),distance(b);return da==db and a.id<b.id or da<db
    end)
    return hits
end
local function decode(data,catalog)
    local value=require('json').decode(data)
    assert(type(value)=='table' and value.schema_version==1 and type(value.areas)=='table','Invalid exit-area file')
    local allowed={}
    for key in pairs(catalog.maps) do
        allowed[key]={};for _,exit in ipairs(catalog.exits(key)) do allowed[key][exit.id]=true end
    end
    for map,entries in pairs(value.areas) do
        assert(allowed[map] and type(entries)=='table','Unknown map in exit areas')
        for id,r in pairs(entries) do assert(allowed[map][id] and H.valid(r),'Invalid exit area: '..map..'/'..tostring(id)) end
    end
    return value.areas
end
local function read(path)
    local f=io.open(path,'rb');if not f then return nil end
    local data=f:read('*a');f:close();return data
end
function H.load(store,path,catalog)
    if not path then return true end
    local data=read(path);if not data then return true end
    local ok,areas=pcall(decode,data,catalog)
    if not ok then
        local backup=read(path..'.bak')
        if backup then ok,areas=pcall(decode,backup,catalog) end
        if not ok then return false,'Exit-area file could not be read; existing file kept.' end
    end
    store.areas=areas;store.saved=clone(areas);store.undo={};store.dirty=false
    return true
end
local function write(path,data)
    local f,err=io.open(path,'wb');if not f then return false,err end
    local ok,message=f:write(data);local closed,close_err=f:close()
    if not ok or not closed then return false,message or close_err end
    return true
end
function H.save(store,path,catalog)
    if not path then return false,'Exit-area save location is unavailable.' end
    local folder=path:match('^(.*)[/\\][^/\\]+$')
    if folder and ashita and ashita.fs then ashita.fs.create_directory(folder) end
    local previous=read(path)
    if previous and pcall(decode,previous,catalog) then
        local ok=write(path..'.bak',previous)
        if not ok then return false,'Could not back up exit areas; changes are still unsaved.' end
    end
    local ok,err=write(path,require('json').encode({schema_version=1,areas=store.areas}))
    if not ok then return false,'Could not save exit areas: '..tostring(err) end
    store.saved=clone(store.areas);store.dirty=false;return true
end
return H
