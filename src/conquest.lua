-- Conquest ownership from the client's 0x05E response to a 0x05A request.
-- Region order and byte offsets follow the HorizonXI-compatible Tally addon.
local M={owners={}}
local regions={
    ronfaure=1,zulkheim=2,norvallen=3,gustaberg=4,derfland=5,
    sarutabaruta=6,kolshushu=7,aragoneu=8,fauregandi=9,valdeaunia=10,
    qufim=11,litelor=12,kuzotz=13,vollbow=14,
    ['elshimo-lowlands']=15,['elshimo-uplands']=16,
    tavnazia=19,
}
M.nations={
    -- ImGui draw colors are packed ABGR, not CSS-style ARGB.
    [0]={name="San d'Oria",color=0xFF493BE6}, -- vivid red
    [1]={name='Bastok',color=0xFFF09F5A}, -- blue
    [2]={name='Windurst',color=0xFF70CA56}, -- green
    [3]={name='Beastmen',color=0xFF4AADE8}, -- amber
}
M.unknown={name='Unknown',color=0xFFABAFA8}
function M.ingest(data)
    if type(data)~='string' or #data<0x66 then return false end
    local owners={}
    for region=1,19 do
        local raw=data:byte(0x1D+(region-1)*4+1)
        owners[region]=raw>=1 and raw<=4 and raw-1 or nil
    end
    M.owners=owners
    return true
end
function M.owner(id)
    local region=id and id:match('^outpost%-(.+)$')
    local nation=region and M.owners[regions[region]]
    return M.nations[nation] or M.unknown
end
function M.request()
    local manager=AshitaCore and AshitaCore:GetPacketManager()
    if manager then manager:AddOutgoingPacket(0x05A,{0,0,0,0}) end
end
local function delayed_request(seconds)
    if ashita.tasks and ashita.tasks.once then ashita.tasks.once(seconds,M.request) end
end
function M.start()
    M.owners={}
    delayed_request(1)
end
function M.zoned()
    M.owners={}
    delayed_request(3)
end
return M
