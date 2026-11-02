-- Stable zone-ID corrections to world click targets; map artwork is unchanged.
local Store=require('src.poi_edits')
local C=require('src.catalog')
local S={base=require('data.world_art')}
S.store={changes={},saved={},undo={},dirty=false}
function S.id(node) return node.id or 'zone-'..C.maps[node.maps[1]].zone end
function S.valid(r,data)
    if type(r)~='table' or #r~=4 then return false end
    for i,v in ipairs(r) do if type(v)~='number' or v~=v or v<0 or v>(i%2==1 and data.width or data.height) then return false end end
    return r[3]-r[1]>=2 and r[4]-r[2]>=2
end
function S.validate(doc,data)
    assert(type(doc)=='table' and doc.schema_version==1 and doc.kind=='world_selectors' and type(doc.selectors)=='table','Invalid world selector file')
    local ids={};for _,node in ipairs(data.zones) do ids[S.id(node)]=true end
    for id,r in pairs(doc.selectors) do assert(ids[id] and S.valid(r,data),'Invalid world selector: '..tostring(id)) end
    return Store.clone(doc.selectors)
end
function S.correct(data,changes)
    local result=Store.clone(data)
    for _,node in ipairs(result.zones) do
        local r=changes[S.id(node)]
        if r then node.bounds=Store.clone(r);node.custom_bounds=true end
    end
    return result
end
S.data=S.correct(S.base,{})
function S.refresh()
    -- Keep the shared world descriptor stable for navigation and tile loading.
    S.data.zones=S.correct(S.base,S.store.changes).zones
end
function S.node(id)
    for _,node in ipairs(S.data.zones) do if S.id(node)==id then return node end end
end
function S.bounds(node,scale,measure)
    local r=node.bounds
    if node.supplementary and not node.custom_bounds and measure then
        local w,h=measure(node.title);local x,y=(r[1]+r[3])/2,(r[2]+r[4])/2
        return {x-(w/2+6)/scale,y-(h/2+4)/scale,x+(w/2+6)/scale,y+(h/2+4)/scale}
    end
    return Store.clone(r)
end
function S.set(id,r)
    if r and not S.valid(r,S.data) then return false end
    local changes=Store.clone(S.store.changes);changes[id]=Store.clone(r)
    local changed=Store.set(S.store,changes);S.refresh();return changed
end
function S.undo() Store.undo(S.store);S.refresh() end
function S.document() return {schema_version=1,kind='world_selectors',coordinate_space='Atlas world canvas pixels',selectors=Store.clone(S.store.changes)} end
local function read(path)
    local f=path and io.open(path,'rb');if not f then return end
    local raw=f:read('*a');f:close();return raw
end
local function decode(raw) return S.validate(require('json').decode(raw),S.base) end
function S.load(path)
    local raw=read(path);if not raw then return true end
    local ok,changes=pcall(decode,raw)
    if not ok then local backup=read(path..'.bak');if backup then ok,changes=pcall(decode,backup) end end
    if not ok then S.store.blocked=true;return false,'World selectors could not be read; existing file kept.' end
    S.store={changes=changes,saved=Store.clone(changes),undo={},dirty=false};S.refresh();return true
end
local function write(path,raw)
    local f,err=io.open(path,'wb');if not f then return false,err end
    local ok,message=f:write(raw);local closed,close_err=f:close();return ok and closed,message or close_err
end
function S.save(path)
    if S.store.blocked then return false,'Unreadable world selector file kept; restore it before saving.' end
    if not path then return false,'World selector save location is unavailable.' end
    if not pcall(S.validate,S.document(),S.base) then return false,'Invalid world selectors; changes are still unsaved.' end
    local folder=path:match('^(.*)[/\\][^/\\]+$')
    if folder and ashita and ashita.fs then ashita.fs.create_directory(folder) end
    local previous=read(path)
    if previous and pcall(decode,previous) and not write(path..'.bak',previous) then return false,'Could not back up world selectors; changes are still unsaved.' end
    local ok,err=write(path,require('json').encode(S.document()))
    if not ok then return false,'Could not save world selectors: '..tostring(err) end
    S.store.saved=Store.clone(S.store.changes);S.store.dirty=false;return true
end
return S
