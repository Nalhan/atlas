-- Client map table, native floor lookup and coordinate transform follow the
-- approaches documented by looney's Boussole (see README credits).
local ffi=require('ffi')
local d3d8=require('d3d8')
require('d3d8.d3dx8')
local image=require('src.dat_image')
local M={ cache={}, table_ptr=0, zoning=false }
local asset_age=0
ffi.cdef[[
    typedef struct AtlasFile AtlasFile;
    int fopen_s(AtlasFile** file, const char* name, const char* mode);
    int fclose(AtlasFile* file);
    int fseek(AtlasFile* file, long offset, int origin);
    long ftell(AtlasFile* file);
    size_t fread(void* buffer, size_t size, size_t count, AtlasFile* file);
    typedef int32_t (__thiscall* AtlasFloorFn)(void*, float, float, float);
]]
local function signed(v,range) return v>=range/2 and v-range or v end
function M.init()
    local mem=ashita.memory
    local addr=mem.find('FFXiMain.dll',0,'8A0D????????5333C05684C95774??8A5424188B7424148B7C2410B9',0,0)
    if addr and addr~=0 then M.table_ptr=mem.read_uint32(addr+0x1C) end
    local fn=mem.find('FFXiMain.dll',0,'8B542408568D4424108BF18B4C2410508B44240C',0,0)
    local obj=mem.find('FFXiMain.dll',0,'8B7424148B4424108B7C240C8B0D',0x0E,0)
    if fn and fn~=0 and obj and obj~=0 then M.floor_fn=ffi.cast('AtlasFloorFn',fn); M.floor_ptr=obj end
end
function M.entry(def)
    if not def.index or M.table_ptr==0 then return nil end
    local m=ashita.memory; local p=M.table_ptr+def.index*14
    -- Fail closed on a client whose table differs from this curated slice.
    if m.read_uint16(p)~=def.zone or m.read_uint8(p+2)~=def.floor then return nil end
    local flags=m.read_uint8(p+4)%16
    local bases={[0]=5312,[1]=53295,[2]=54295}
    return { scale=signed(m.read_uint8(p+5),256), ox=signed(m.read_uint16(p+10),65536),
        oy=signed(m.read_uint16(p+12),65536), dat=bases[flags] and bases[flags]+m.read_uint16(p+8) }
end
local function read_dat(id)
    local path=AshitaCore:GetResourceManager():GetFilePath(id)
    if not path or path=='' then return nil,'No DAT path for file '..id end
    -- Use CRT fopen_s so XIPivot can redirect the read, as in Boussole.
    local fp=ffi.new('AtlasFile*[1]')
    local code=ffi.C.fopen_s(fp,path,'rb')
    if code~=0 or fp[0]==nil then
        if fp[0]~=nil then ffi.C.fclose(fp[0]) end
        return nil,'Cannot read '..path
    end
    local f=fp[0]
    if ffi.C.fseek(f,0,2)~=0 then ffi.C.fclose(f); return nil,'DAT seek failed.' end
    local size=tonumber(ffi.C.ftell(f))
    if size<109 or size>128*1024*1024 then ffi.C.fclose(f); return nil,'Invalid DAT size.' end
    if ffi.C.fseek(f,0,0)~=0 then ffi.C.fclose(f); return nil,'DAT rewind failed.' end
    local buffer=ffi.new('uint8_t[?]',size)
    local count=tonumber(ffi.C.fread(buffer,1,size,f)); ffi.C.fclose(f)
    if count~=size then return nil,'Incomplete DAT read.' end
    return ffi.string(buffer,size),nil,path
end
local function remapster_art(data,path)
    -- Detect the actual bytes loaded through Pivot; HD dimensions alone do not
    -- tell us whether a map contains Remapster's printed exit badges.
    local relative=path:gsub('\\','/'):lower():match('(rom%d*/%d+/%d+%.dat)$')
    if not relative then return false end
    local file=io.open(AshitaCore:GetInstallPath()..'polplugins/DATs/remapster/'..relative,'rb')
    if not file then return false end
    local candidate=file:read('*a');file:close()
    return candidate==data
end
function M.texture(def)
    local key=def.key or 'world'
    if M.cache[key] then return M.cache[key] end
    if not def.dat then return nil,'This area has no standard client map.' end
    local entry=M.entry(def)
    local data,err,path=read_dat(entry and entry.dat or def.dat)
    if not data then M.cache[key]={error=err}; return M.cache[key] end
    local wrapped,w,h=image.wrap(data)
    if not wrapped then M.cache[key]={error=w}; return M.cache[key] end
    local ptr=ffi.new('IDirect3DTexture8*[1]')
    local hr=ffi.C.D3DXCreateTextureFromFileInMemory(d3d8.get_device(),wrapped,#wrapped,ptr)
    if hr~=0 or ptr[0]==nil then
        if ptr[0]~=nil then ptr[0]:Release() end
        M.cache[key]={error='Could not create map texture ('..tonumber(hr)..').'}
    else
        -- Keep the owning reference until explicit release on retry / unload.
        M.cache[key]={owner=ptr[0],id=tonumber(ffi.cast('uintptr_t',ptr[0])),width=w,height=h,entry=entry,
            remapster=remapster_art(data,path)}
    end
    return M.cache[key]
end
function M.clear()
    for _,t in pairs(M.cache) do if t.owner then t.owner:Release(); t.owner=nil end end
    M.cache={}
end
function M.peek_asset(path)
    local texture=M.cache['asset:'..path]
    if texture then asset_age=asset_age+1;texture.last_used=asset_age end
    return texture
end
function M.asset(path)
    local cached=M.peek_asset(path)
    if cached then return cached end
    local key='asset:'..path
    local file=io.open(AshitaCore:GetInstallPath()..'addons/atlas/'..path,'rb')
    if not file then M.cache[key]={error='Map artwork unavailable'};return M.cache[key] end
    local data=file:read('*a');file:close()
    local function be32(offset)
        local a,b,c,d=data:byte(offset,offset+3)
        return d and ((a*256+b)*256+c)*256+d
    end
    local width,height=be32(17),be32(21)
    if data:sub(1,8)~='\137PNG\r\n\26\n' or not width or not height or width<1 or height<1 or width>2048 or height>2048 then
        M.cache[key]={error='Invalid map texture dimensions'};return M.cache[key]
    end
    local ptr=ffi.new('IDirect3DTexture8*[1]')
    -- The world pyramid already supplies each detail level. Avoid generating
    -- another mip chain during a zoom step or uploading unused mip levels.
    local hr=ffi.C.D3DXCreateTextureFromFileInMemoryEx(d3d8.get_device(),data,#data,
        width,height,1,0,ffi.C.D3DFMT_A8R8G8B8,ffi.C.D3DPOOL_MANAGED,
        ffi.C.D3DX_DEFAULT,ffi.C.D3DX_DEFAULT,0,nil,nil,ptr)
    if hr~=0 or ptr[0]==nil then
        if ptr[0]~=nil then ptr[0]:Release() end
        M.cache[key]={error='Could not load map artwork'}
    else
        M.cache[key]={owner=ptr[0],id=tonumber(ffi.cast('uintptr_t',ptr[0])),width=width,height=height}
    end
    return M.peek_asset(path)
end
function M.keep_assets(paths,limit)
    local keep={};local used=0;local spare={}
    for _,path in ipairs(paths) do keep['asset:'..path]=true end
    for key,texture in pairs(M.cache) do
        if key:sub(1,6)=='asset:' then
            if keep[key] then used=used+1 else spare[#spare+1]={key=key,age=texture.last_used or 0} end
        end
    end
    if limit and used<limit then
        table.sort(spare,function(a,b) return a.age==b.age and a.key<b.key or a.age>b.age end)
        for i=1,math.min(#spare,limit-used) do keep[spare[i].key]=true end
    end
    for key,texture in pairs(M.cache) do
        if key:sub(1,6)=='asset:' and not keep[key] then
            if texture.owner then texture.owner:Release() end
            M.cache[key]=nil
        end
    end
end
function M.floor_at(x,y,z)
    if M.zoning or not M.floor_fn or not M.floor_ptr then return nil end
    local root=ashita.memory.read_uint32(M.floor_ptr)
    local obj=root~=0 and ashita.memory.read_uint32(root) or 0
    if obj~=0 then return tonumber(M.floor_fn(ffi.cast('void*',obj),x,z,y)) end
end
function M.player()
    if M.zoning then return nil end
    local e=GetPlayerEntity()
    local party=AshitaCore:GetMemoryManager():GetParty()
    if not e or not party then return nil end
    local p=e.Movement.LocalPosition
    local result={zone=party:GetMemberZone(0),x=p.X,y=p.Y,z=p.Z,heading=e.Heading or 0,name=e.Name}
    result.floor=M.floor_at(p.X,p.Y,p.Z)
    return result
end
function M.members(player)
    if M.zoning or not player then return {} end
    -- Like Boussole's party/alliance overlays, read live entity positions on
    -- every draw. Caching the snapshot also delayed movement, roster changes,
    -- despawns and identity validation until the cache expired.
    local party=AshitaCore:GetMemoryManager():GetParty()
    local result,seen={},{}
    if not party then return result end
    for slot=1,17 do
        if party:GetMemberIsActive(slot)==1 then
            local id=party:GetMemberServerId(slot)
            local zone=party:GetMemberZone(slot)
            local name=party:GetMemberName(slot)
            if id and id~=0 and zone and zone~=0 and name and name~='' and not seen[id] then
                seen[id]=true
                local member={id=id,name=name,zone=zone,slot=slot,group=slot<=5 and 'party' or 'alliance'}
                -- Coordinates from another zone's target index may refer to an
                -- unrelated entity. Check both the zone and server identity.
                if zone==player.zone then
                    local index=party:GetMemberTargetIndex(slot)
                    local entity=index and index>0 and GetEntity(index) or nil
                    if entity and entity.ServerId==id and entity.Render.Flags0~=0 then
                        local p=entity.Movement.LastPosition
                        member.x,member.y,member.z=p.X,p.Y,p.Z
                        member.heading=entity.Heading or 0
                        member.floor=M.floor_at(p.X,p.Y,p.Z)
                    end
                end
                result[#result+1]=member
            end
        end
    end
    return result
end
function M.position(def,player)
    if not player or player.x==nil or player.y==nil or player.zone~=def.zone or player.floor~=def.floor then return nil end
    local e=M.entry(def)
    if not e or e.scale==0 then return nil end
    return player.x*math.abs(e.scale)/5-e.ox, -player.y*math.abs(e.scale)/5-e.oy
end
return M
