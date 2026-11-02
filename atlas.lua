addon.name='atlas'
addon.author='Horizon prototype'
addon.version='0.8.7'
addon.desc='A connected atlas of Vana\'diel and Aht Urhgan.'
require('common')
local client=require('src.client')
local ui=require('src.ui')
local conquest=require('src.conquest')

ashita.events.register('load','atlas_load',function() require('src.map_labels').load();client.init();ui.load_areas();ui.load_pois();ui.load_selectors();conquest.start() end)
ashita.events.register('unload','atlas_unload',function() ui.save_areas();ui.save_pois();ui.save_selectors();client.clear() end)
ashita.events.register('packet_in','atlas_zoning',function(e)
    if e.id==0x00B then client.zoning=true
    elseif e.id==0x00A then client.zoning=false;conquest.zoned()
    elseif e.id==0x05E then conquest.ingest(e.data) end
end)
ashita.events.register('command','atlas_command',function(e)
    local args=e.command:args()
    if not args[1] or args[1]:lower()~='/atlas' then return end
    e.blocked=true
    local command=(args[2] or ''):lower()
    if command=='' then
        if ui.visible[1] then ui.visible[1]=false else ui.open() end
    elseif command=='hide' then ui.visible[1]=false
    elseif command=='show' then ui.open()
    elseif command=='world' then ui.open('world')
    elseif require('src.world').data.regions[command] then
        ui.open('region',command)
    elseif command=='here' then ui.open()
    elseif command=='selectors' then ui.edit_selectors()
    elseif command=='poi' then ui.edit_pois()
    elseif command=='edit' then ui.edit_exits()
    else print('[Atlas] /atlas [show | hide | world | region name | here | edit | poi | selectors]') end
end)
ashita.events.register('d3d_present','atlas_present',ui.draw)
