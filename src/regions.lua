local helper=require('src.region')
local regions={ronfaure=helper}
local generated=require('data.regions')
for id,board in pairs(require('data.expanded_regions')) do generated[id]=board end
for id,board in pairs(require('data.aht_regions')) do generated[id]=board end
helper.id='ronfaure';helper.title='RONFAURE'
for id,board in pairs(generated) do
    local current=board
    board.routes=function(catalog) return helper.routes_for(current,catalog) end
    board.thumbnail_uv=helper.thumbnail_uv
    board.count_members=helper.count_members
    regions[id]=board
end
local M={order={'ronfaure','zulkheim','norvallen','fauregandi','gustaberg','derfland','valdeaunia','vollbow',
    'qufim','aragoneu','kolshushu','sarutabaruta','litelor','tulia','kuzotz','elshimo_lowlands','elshimo_uplands','tavnazian_archipelago',
    'western_aradjiah','west_aht_urhgan','mamool_ja_savagelands','halvung_territory','arrapago_islands','ruins_of_alzadaal'},
    hotspots={
        ronfaure={126,128,214,193},zulkheim={75,207,175,253},
        norvallen={182,194,274,238},fauregandi={192,76,286,123},
        gustaberg={100,330,190,390},derfland={190,255,290,320},valdeaunia={100,40,190,100},vollbow={35,285,110,330},
        qufim={310,165,360,185},aragoneu={350,215,400,235},kolshushu={410,280,460,300},sarutabaruta={315,310,365,330},
        litelor={415,200,455,220},tulia={330,100,370,120},kuzotz={50,325,90,345},
        elshimo_lowlands={390,410,460,430},elshimo_uplands={445,360,510,380},tavnazian_archipelago={35,200,110,220}
    }}
M.diagrams=regions
local artwork=require('data.regional_art')
for _,board in pairs(artwork) do
    local current=board
    board.routes=function(catalog) return helper.routes_for(current,catalog) end
    board.count_members=helper.count_members
end
function M.diagram(id) return regions[id] or regions.ronfaure end
function M.get(id) return artwork[id] or regions[id] or artwork.ronfaure end
return M
