local W={data=require('src.world_selectors').data}
function W.zone_bounds(key)
    local region=W.data.regions[require('src.catalog').maps[key].region]
    for _,node in ipairs(W.data.zones) do
        for _,map in ipairs(node.maps) do if map==key then
            local b=node.bounds;local r=region.bounds
            local x,y=(b[1]+b[3])/2,(b[2]+b[4])/2
            local w,h=r[3]-r[1],r[4]-r[2]
            return {x-w/2,y-h/2,x+w/2,y+h/2}
        end end
    end
    return region.bounds
end
function W.visible(ox,oy,scale,x,y,width,height,level)
    if not level then
        level=W.data.native_zoom
        while level>W.data.minimum_level and scale*2^(W.data.native_zoom-level+1)<=1.25 do level=level-1 end
    end
    local visible={}
    for _,page in ipairs(W.data.levels[tostring(level)]) do
        local l,t,r,b=ox+page.x*scale,oy+page.y*scale,ox+(page.x+page.w)*scale,oy+(page.y+page.h)*scale
        if r>x and b>y and l<x+width and t<y+height then visible[#visible+1]=page end
    end
    return visible,level
end
-- Keep a coarse complete map underneath cached detail. A wheel gesture never
-- synchronously loads fine tiles; once settled, fill one missing tile per frame.
function W.prepare(client,ox,oy,scale,x,y,width,height,busy)
    local wanted,level=W.visible(ox,oy,scale,x,y,width,height)
    while #wanted>16 and level>W.data.minimum_level do
        level=level-1;wanted=W.visible(ox,oy,scale,x,y,width,height,level)
    end
    local base=W.data.levels[tostring(W.data.minimum_level)][1]
    local texture=client.peek_asset(base.path);local loaded=false
    if not texture then texture=client.asset(base.path);loaded=true end
    if not texture.id then return nil,level end
    if not busy and not loaded then
        local missing={}
        for _,page in ipairs(wanted) do
            if not client.peek_asset(page.path) then missing[#missing+1]=page end
        end
        table.sort(missing,function(a,b)
            local function distance(p) return (ox+(p.x+p.w/2)*scale-x-width/2)^2+(oy+(p.y+p.h/2)*scale-y-height/2)^2 end
            return distance(a)<distance(b)
        end)
        if missing[1] then client.asset(missing[1].path) end
    end
    local ready,paths={},{}
    for lod=W.data.minimum_level,level do
        local pages=W.visible(ox,oy,scale,x,y,width,height,lod)
        for _,page in ipairs(pages) do
            local cached=client.peek_asset(page.path)
            if cached and cached.id then
                ready[#ready+1]={page=page,id=cached.id}
            end
        end
    end
    -- On large windows, several cached fallback levels can overlap. Prefer
    -- current detail over intermediate fallbacks, retaining the complete base.
    while #ready>24 do table.remove(ready,2) end
    for _,tile in ipairs(ready) do paths[#paths+1]=tile.page.path end
    paths[#paths+1]=base.path
    client.keep_assets(paths,24)
    return ready,level
end
return W
