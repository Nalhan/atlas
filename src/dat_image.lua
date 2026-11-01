-- Pure Lua DAT -> DDS/BMP wrapping. No texture pixels are bundled with Atlas.
-- Formats and offsets were checked against the installed Boussole loader.
local D={}
local function u16(s,p) local a,b=s:byte(p+1,p+2); return a+b*256 end
local function u32(s,p) return u16(s,p)+u16(s,p+2)*65536 end
local function le(n,bytes)
    local t={}; for i=1,bytes do t[i]=string.char(n%256); n=math.floor(n/256) end
    return table.concat(t)
end
function D.wrap(data)
    if #data<109 then return nil,'DAT image header is truncated.' end
    local w,h=u32(data,69),u32(data,73)
    local bits,kind=u16(data,79),u32(data,105)
    if w<1 or h<1 or w>8192 or h>8192 then return nil,'Invalid DAT dimensions.' end
    local formats={[0x44585431]='DXT1',[0x44585432]='DXT2',[0x44585433]='DXT3',
        [0x44585434]='DXT4',[0x44585435]='DXT5'}
    if formats[kind] then
        local count=math.ceil(w/4)*math.ceil(h/4)*(kind==0x44585431 and 8 or 16)
        if #data<117+count then return nil,'Compressed DAT pixels are truncated.' end
        local header=le(124,4)..le(0x81007,4)..le(h,4)..le(w,4)..le(count,4)..string.rep('\0',52)
            ..le(32,4)..le(4,4)..formats[kind]..string.rep('\0',20)..le(0x1000,4)..string.rep('\0',16)
        return 'DDS '..header..data:sub(118,117+count),w,h
    end
    if kind~=10 or (bits~=8 and bits~=24 and bits~=32) then
        return nil,'Unsupported DAT image format / depth.'
    end
    local palette=bits==8 and 1024 or 0
    local row=w*bits/8
    local stride=math.floor((row+3)/4)*4
    local count=w*h*bits/8
    if #data<109+palette+count then return nil,'Bitmap DAT pixels are truncated.' end
    local offset=54+palette
    local info=le(40,4)..le(w,4)..le(h,4)..le(1,2)..le(bits,2)..le(0,4)..le(stride*h,4)
        ..string.rep('\0',8)..le(bits==8 and 256 or 0,4)..le(0,4)
    local rows={}
    for y=0,h-1 do
        local p=109+palette+y*row
        rows[#rows+1]=data:sub(p+1,p+row)..string.rep('\0',stride-row)
    end
    -- A positive BMP height preserves the DAT's bottom-up row order.
    return 'BM'..le(offset+stride*h,4)..string.rep('\0',4)..le(offset,4)..info
        ..data:sub(110,109+palette)..table.concat(rows),w,h
end
return D
