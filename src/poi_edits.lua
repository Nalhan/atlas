-- Portable, stable-ID corrections; generated POI data is never written in game.
local E={}
function E.clone(v)
    if type(v)~='table' then return v end
    local out={};for k,x in pairs(v) do out[k]=E.clone(x) end;return out
end
local function equal(a,b)
    if type(a)~=type(b) then return false end
    if type(a)~='table' then return a==b end
    for k,v in pairs(a) do if not equal(v,b[k]) then return false end end
    for k in pairs(b) do if a[k]==nil then return false end end
    return true
end
function E.new() return {changes={world={},stops={}},saved={world={},stops={}},undo={},dirty=false} end
local function dirty(store) store.dirty=not equal(store.changes,store.saved) end
function E.set(store,changes)
    if equal(store.changes,changes) then return false end
    table.insert(store.undo,E.clone(store.changes));if #store.undo>100 then table.remove(store.undo,1) end
    store.changes=E.clone(changes);dirty(store);return true
end
function E.undo(store)
    local previous=table.remove(store.undo);if previous then store.changes=previous;dirty(store) end
end
local function coordinate(n,max)
    return type(n)=='number' and n==n and n>=0 and n<=max
end
function E.validate(value,data,catalog,world)
    assert(type(value)=='table' and value.schema_version==1,'Unsupported POI corrections file')
    local c=value.changes
    assert(type(c)=='table' and type(c.world)=='table' and type(c.stops)=='table','Missing POI corrections')
    local ids={};for _,stop in ipairs(data.stops) do ids[stop.id]=true end
    for id,p in pairs(c.world) do
        assert(data.hubs[id] and type(p)=='table' and coordinate(p.x,world.width) and coordinate(p.y,world.height),'Invalid world POI: '..tostring(id))
        for k in pairs(p) do assert(k=='x' or k=='y','Unknown world POI field') end
    end
    for id,p in pairs(c.stops) do
        assert(ids[id] and type(p)=='table','Unknown POI: '..tostring(id))
        for k in pairs(p) do assert(k=='map' or k=='x' or k=='y' or k=='hidden','Unknown POI field') end
        assert(p.hidden==nil or type(p.hidden)=='boolean','Invalid POI visibility')
        if p.map~=nil or p.x~=nil or p.y~=nil then
            local def=catalog.maps[p.map]
            assert(def and (def.dat or def.asset) and coordinate(p.x,512) and coordinate(p.y,512),'Invalid zone POI: '..id)
        end
    end
    return E.clone(c)
end
function E.apply(data,changes,catalog)
    local result=E.clone(data)
    for id,p in pairs(changes.world) do result.hubs[id].world={p.x,p.y} end
    for _,stop in ipairs(result.stops) do
        local p=changes.stops[stop.id]
        if p then
            if p.map then stop.map=p.map;stop.x=p.x;stop.y=p.y;stop.area=catalog.maps[p.map].name end
            if p.hidden~=nil then stop.hidden=p.hidden end
            stop.corrected=true
        end
    end
    return result
end
function E.document(store)
    return {schema_version=1,coordinate_spaces={world='Atlas world canvas pixels',zone='512x512 map pixels'},changes=E.clone(store.changes)}
end
local function read(path)
    local f=path and io.open(path,'rb');if not f then return nil end
    local value=f:read('*a');f:close();return value
end
local function decode(raw,data,catalog,world) return E.validate(require('json').decode(raw),data,catalog,world) end
function E.load(store,path,data,catalog,world)
    local raw=read(path);if not raw then return true end
    local ok,changes=pcall(decode,raw,data,catalog,world)
    if not ok then
        local backup=read(path..'.bak')
        if backup then ok,changes=pcall(decode,backup,data,catalog,world) end
        if not ok then store.blocked=true;return false,'POI corrections could not be read; file kept. Restore it before saving.' end
    end
    store.changes=changes;store.saved=E.clone(changes);store.undo={};store.dirty=false;store.blocked=nil
    return true
end
local function write(path,raw)
    local f,err=io.open(path,'wb');if not f then return false,err end
    local ok,message=f:write(raw);local closed,close_err=f:close();return ok and closed,message or close_err
end
function E.save(store,path,data,catalog,world)
    if store.blocked then return false,'Unreadable POI file kept; restore it before saving.' end
    if not path then return false,'POI save location is unavailable.' end
    local ok=pcall(E.validate,E.document(store),data,catalog,world)
    if not ok then return false,'Invalid POI corrections; changes are still unsaved.' end
    local folder=path:match('^(.*)[/\\][^/\\]+$')
    if folder and ashita and ashita.fs then ashita.fs.create_directory(folder) end
    local previous=read(path)
    if previous and pcall(decode,previous,data,catalog,world) then
        if not write(path..'.bak',previous) then return false,'Could not back up POI corrections; changes are still unsaved.' end
    end
    local saved,err=write(path,require('json').encode(E.document(store)))
    if not saved then return false,'Could not save POI corrections: '..tostring(err) end
    store.saved=E.clone(store.changes);store.dirty=false;return true
end
return E
