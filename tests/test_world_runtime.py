"""Bounded texture fidelity, viewport culling and zoom geometry."""
from pathlib import Path
import hashlib
import json
import unittest
from PIL import Image,ImageChops
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]

class WorldRuntime(unittest.TestCase):
    def test_texture_pages_preserve_the_connected_artwork(self):
        lua=LuaRuntime();lua.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        data=lua.eval("require('data.world_art')")
        source=json.loads((ADDON/'assets/world/SOURCES.json').read_text())
        master_path=ADDON/'exports/horizon-connected-z5/connected-world.png'
        self.assertEqual(hashlib.sha256(master_path.read_bytes()).hexdigest(),source['master_sha256'])
        master=Image.open(master_path).convert('RGB');checked=set()
        for level,pages in data['levels'].items():
            side=256*2**int(level);factor=8192//side
            expected=master if int(level)==5 else master.resize((side,side),Image.Resampling.LANCZOS)
            self.assertEqual(len(pages),(side//1024)**2)
            for _,page in pages.items():
                path=page['path'];checked.add(path)
                self.assertEqual(hashlib.sha256((ADDON/path).read_bytes()).hexdigest(),source['assets'][path])
                image=Image.open(ADDON/path).convert('RGB');self.assertEqual(image.size,(1024,1024))
                x,y=page['x']//factor,page['y']//factor
                self.assertIsNone(ImageChops.difference(image,expected.crop((x,y,x+1024,y+1024))).getbbox())
        self.assertEqual(checked,set(source['assets']))

    def test_visible_pages_zoom_limits_and_pointer_anchor(self):
        lua=LuaRuntime();lua.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        lua.execute('''
        local W=require('src.world');local N=require('src.navigation')
        local fit={cx=4096,cy=4096,zoom=1,zoom_max=W.data.maximum_zoom}
        local ox,oy,s=N.transform(fit,0,0,1100,760,8192,8192)
        local pages,level=W.visible(ox,oy,s,0,0,1100,760)
        assert(level==2 and #pages==1)
        local px,py=(300-ox)/s,(200-oy)/s
        N.zoom_at(fit,100,300,200,0,0,1100,760,8192,8192)
        assert(fit.zoom==32)
        ox,oy,s=N.transform(fit,0,0,1100,760,8192,8192)
        assert(math.abs(ox+px*s-300)<1e-7 and math.abs(oy+py*s-200)<1e-7)
        pages,level=W.visible(ox,oy,s,0,0,1100,760);assert(level==5 and #pages<=4)
        for _,zoom in ipairs({1,2,4,8,16,32}) do
            for _,center in ipairs({{4096,4096},{0,0},{8192,8192},{3000,2700}}) do
                local v={cx=center[1],cy=center[2],zoom=zoom}
                ox,oy,s=N.transform(v,0,0,1100,760,8192,8192)
                pages=W.visible(ox,oy,s,0,0,1100,760);assert(#pages<=16)
                for _,p in ipairs(pages) do
                    assert(ox+(p.x+p.w)*s>0 and ox+p.x*s<1100)
                    assert(oy+(p.y+p.h)*s>0 and oy+p.y*s<760)
                end
            end
        end
        assert(#W.visible(-20000,-20000,1,0,0,1100,760)==0)
        ''')

    def test_progressive_loading_gesture_deferral_and_warm_cache(self):
        lua=LuaRuntime();lua.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        lua.execute('''
        package.loaded.d3d8={};package.loaded['d3d8.d3dx8']={}
        local client=require('src.client');local W=require('src.world');local N=require('src.navigation')
        local loads,releases=0,0
        client.asset=function(path)
            local cached=client.peek_asset(path)
            if cached then return cached end
            loads=loads+1
            client.cache['asset:'..path]={id=path,owner={Release=function() releases=releases+1 end}}
            return client.peek_asset(path)
        end
        local function frame(zoom,busy,cx,cy,w,h)
            w,h=w or 1100,h or 760
            local v={cx=cx or 3100,cy=cy or 3400,zoom=zoom}
            local ox,oy,s=N.transform(v,0,0,w,h,8192,8192)
            local before=loads
            local ready,level=W.prepare(client,ox,oy,s,0,0,w,h,busy)
            assert(loads-before<=1,'A frame loaded multiple textures')
            assert(ready and #ready>0 and ready[1].page.path==W.data.levels['2'][1].path,'Missing coarse fallback')
            local count=0;for _ in pairs(client.cache) do count=count+1 end
            assert(count<=24,'World cache exceeded its budget')
            return ready,level
        end
        frame(1,false);assert(loads==1)
        for _,zoom in ipairs({2,4,8,16,32,16,8}) do frame(zoom,true) end
        assert(loads==1,'Active gesture performed fine texture uploads')
        for _,zoom in ipairs({2,4,8}) do for i=1,16 do frame(zoom,false) end end
        local warm=loads
        for _,zoom in ipairs({4,2,1,2,4,8}) do for i=1,16 do frame(zoom,false) end end
        assert(loads==warm,'Returning to warm zoom levels reloaded textures')
        local released_before=releases
        for x=1024,7168,2048 do for y=1024,7168,2048 do
            for i=1,16 do frame(8,false,x,y) end
        end end
        assert(releases>released_before,'Cache did not evict old areas')
        for i=1,16 do frame(5,false) end
        client.keep_assets({},24);local before=loads;frame(5,false)
        assert(loads==before,'Returning from a zone discarded warm world textures')
        for _,zoom in ipairs({1,2,3,4,8,4,3,2,1}) do
            for i=1,20 do frame(zoom,false,3100,3400,2400,1800) end
        end
        client.clear();assert(next(client.cache)==nil)
        ''')

if __name__=='__main__':unittest.main()
