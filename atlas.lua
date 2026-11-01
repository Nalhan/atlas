addon.name='atlas'
addon.author='Horizon prototype'
addon.version='0.7.0'
addon.desc='A connected atlas of Vana\'diel and its western regions.'
require('common')
local client=require('src.client')
local ui=require('src.ui')

ashita.events.register('load','atlas_load',function() client.init();ui.load_areas() end)
ashita.events.register('unload','atlas_unload',function() ui.save_areas();client.clear() end)
ashita.events.register('packet_in','atlas_zoning',function(e)
    if e.id==0x00B then client.zoning=true
    elseif e.id==0x00A then client.zoning=false end
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
    elseif command=='edit' then ui.edit_exits()
    else print('[Atlas] /atlas [show | hide | world | region name | here | edit]') end
end)
ashita.events.register('d3d_present','atlas_present',ui.draw)
