-- Load once, outside a frame; the shared ImGui font atlas owns the font.
local imgui=require('imgui')
local L={size=16,pixel_size=16,min_size=10,max_size=24,reference_scale=0.34,max_width=180,cache={}}
function L.load()
    if L.loaded then return end
    L.loaded=true
    local root=os.getenv('WINDIR') or 'C:\\Windows'
    local path=root..'\\Fonts\\georgiab.ttf';local file=io.open(path,'rb')
    if file then
        file:close()
        local ok,font=pcall(imgui.AddFontFromFileTTF,path,L.size)
        if ok then L.font=font end
    end
    L.cache={}
end
-- Quantized sizes bound the glyph/measurement cache while following map scale.
function L.set_scale(scale)
    L.pixel_size=math.max(L.min_size,math.min(L.max_size,2*math.floor(L.size*scale/L.reference_scale/2+.5)))
end
local function push() imgui.PushFont(L.font or imgui.GetFont(),L.pixel_size) end
local function layout(value)
    local cache=L.cache[L.pixel_size]
    if not cache then cache={};L.cache[L.pixel_size]=cache end
    if cache[value] then return cache[value] end
    push()
    local lines,line={},''
    for word in value:gmatch('%S+') do
        local candidate=line=='' and word or line..' '..word
        local w=imgui.CalcTextSize(candidate)
        if line~='' and w>L.max_width*L.pixel_size/L.size then lines[#lines+1]=line;line=word else line=candidate end
    end
    lines[#lines+1]=line
    local label=table.concat(lines,'\n');local w,h=imgui.CalcTextSize(label)
    imgui.PopFont()
    local result={text=label,w=w,h=h};cache[value]=result;return result
end
function L.measure(value) local item=layout(value);return item.w,item.h end
function L.draw(draw,x,y,value,eastern)
    local item=layout(value);local a,b=x-item.w/2,y-item.h/2
    push()
    draw:AddText({a+1,b+1},eastern and 0xCCDAEAD9 or 0xFF14231C,item.text)
    draw:AddText({a,b},eastern and 0xFF1C2D38 or 0xFFE7EBD9,item.text)
    imgui.PopFont()
end
return L
