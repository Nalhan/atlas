"""Click geometry, editor gestures and real JSON persistence through LuaJIT."""
from pathlib import Path
import tempfile
import unittest
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]

class ExitAreas(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("package.path=... .. '/?.lua;' .. package.path",ADDON.as_posix())
        self.lua.execute("package.path=... .. '/?.lua;' .. package.path",(ADDON.parent/'libs').as_posix())
        self.lua.execute("""
        T=function(v) return v end
        H=require('src.hotspots');E=require('src.exit_editor');C=require('src.catalog')
        store=H.new();exit={id='sample',source={x=100,y=200,badge_x=180,badge_y=240}}
        """)

    def test_default_covers_graphic_between_anchors_and_overlaps(self):
        self.lua.execute("""
        local r=H.default(exit)
        assert(H.contains(r,140,220)) -- gap between old circular click targets
        assert(H.contains(r,80,190)) -- larger catchment beyond the old 18px radius
        assert(not H.contains(r,20,20))
        local other={id='other',source={x=140,y=220}}
        assert(#H.hits(store,'west',{exit,other},140,220)==2)
        assert(not H.valid({0,0,0/0,20}) and not H.valid({-1,0,20,20}))
        assert(H.default({source={x=0,y=512}})[1]==0)
        """)

    def test_undo_reset_and_endpoint_isolation(self):
        self.lua.execute("""
        local a=C.exits('west')[1];local map=a.target.map
        local source_x,target_x=a.source.x,a.target.x
        assert(H.set(store,'west',a.id,{20,30,70,90}) and store.dirty)
        assert(H.get(store,'west',a)[1]==20)
        assert(a.source.x==source_x and a.target.x==target_x)
        assert(not (store.areas[map] and store.areas[map][a.id]))
        H.set(store,'west',a.id,nil);assert(not store.dirty)
        H.undo(store);assert(store.dirty and H.get(store,'west',a)[1]==20)
        H.undo(store);assert(not store.dirty)
        """)

    def test_draw_move_resize_cancel_and_map_switch(self):
        self.lua.execute("""
        local exits={exit};E.prepare('west',exits);E.tool='draw'
        E.pointer(store,'west',exits,30,40,2,true,true,true,false)
        E.pointer(store,'west',exits,90,100,2,true,false,true,false)
        assert(not store.dirty and E.drag.preview[3]==90)
        E.pointer(store,'west',exits,90,100,2,true,false,false,true)
        assert(store.dirty and #store.undo==1)
        E.pointer(store,'west',exits,60,70,2,true,true,true,false)
        E.pointer(store,'west',exits,-200,-200,2,false,false,false,true)
        local r=H.get(store,'west',exit);assert(r[1]==0 and r[2]==0 and r[3]==60 and r[4]==60)
        E.pointer(store,'west',exits,60,60,2,true,true,true,false)
        E.pointer(store,'west',exits,80,90,2,true,false,false,true)
        r=H.get(store,'west',exit);assert(r[3]==80 and r[4]==90)
        E.tool='draw';E.pointer(store,'west',exits,10,10,2,true,true,true,false)
        E.cancel();assert(#store.undo==3 and not E.drag)
        E.tool='draw';E.pointer(store,'west',exits,10,10,2,true,true,true,false)
        E.prepare('east',exits);assert(not E.drag and E.tool=='select')
        """)

    def test_save_reload_backup_and_write_failure(self):
        with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=ADDON/'tests') as temp:
            path=Path(temp)/'exit-areas.json'
            self.lua.globals().save_path=path.as_posix()
            self.lua.execute("""
            local a=C.exits('west')[1];saved_id=a.id
            H.set(store,'west',a.id,{20,30,80,90});assert(H.save(store,save_path,C))
            assert(not store.dirty)
            local loaded=H.new();assert(H.load(loaded,save_path,C))
            assert(H.get(loaded,'west',a)[1]==20)
            H.set(store,'west',a.id,{25,35,85,95});assert(H.save(store,save_path,C))
            H.set(store,'west',a.id,{30,40,90,100})
            local original=io.open
            io.open=function(p,mode) if p==save_path..'.bak' and mode=='wb' then return nil,'denied' end;return original(p,mode) end
            assert(not H.save(store,save_path,C) and store.dirty)
            io.open=original
            """)
            self.assertIn('schema_version',path.read_text())
            path.write_text('{broken JSON',encoding='utf-8')
            self.lua.execute("""
            local loaded=H.new();assert(H.load(loaded,save_path,C))
            assert(loaded.areas.west[saved_id][1]==20) -- previous good save
            """)
            self.lua.execute("""
            local original=io.open
            io.open=function(p,mode) if mode=='wb' then return nil,'denied' end;return original(p,mode) end
            assert(not H.save(store,save_path,C) and store.dirty)
            io.open=original
            """)

if __name__=='__main__':unittest.main()
