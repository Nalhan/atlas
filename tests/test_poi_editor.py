"""POI corrections: real persistence, independent coordinate spaces and release gestures."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]

class PoiEditor(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("package.path=... .. '/?.lua;' .. package.path",ADDON.as_posix())
        self.lua.execute("package.path=... .. '/?.lua;' .. package.path",(ADDON.parent/'libs').as_posix())
        self.lua.execute("""
        T=function(v) return v end
        P=require('src.pois');E=require('src.poi_editor');D=require('src.poi_edits')
        C=require('src.catalog');W=require('src.world').data
        id='outpost-ronfaure';E.selected=id
        """)

    def test_world_native_independence_reassignment_hide_undo(self):
        self.lua.execute("""
        local old=P.stops[id];local x,y=old.x,old.y
        local world={level='world'}
        E.place(world,{old},4000,3000)
        assert(P.hubs[old.hub].world[1]==4000 and P.stops[id].x==x)
        E.place({level='zone',key='east'},{P.stops[id]},100,200)
        assert(P.stops[id].map=='east' and P.stops[id].y==200)
        assert(P.hubs[old.hub].world[1]==4000 and P.base.hubs[old.hub].world[1]~=4000)
        E.hide();assert(P.stops[id].hidden)
        local function count(editing)
            local n=0;for _,m in ipairs(P.markers({level='zone',key='east'},P.filters(),editing)) do
                for _,s in ipairs(m.stops) do if s.id==id then n=n+1 end end
            end;return n
        end
        assert(count(false)==0 and count(true)==1)
        D.undo(P.edits);P.refresh();assert(not P.stops[id].hidden)
        E.reset({level='zone'});assert(P.stops[id].map=='west' and P.stops[id].x==x)
        assert(P.hubs[old.hub].world[1]==4000)
        E.reset(world);assert(not P.edits.dirty)
        """)

    def test_scaled_drag_shared_dock_and_cancel(self):
        self.lua.execute("""
        local view={level='zone',key='mhaura'}
        local markers=P.markers(view,P.filters(),true);assert(#markers==1 and #markers[1].stops==2)
        local m=markers[1];local scale=3;local x,y=m.x,m.y
        assert(E.pointer(view,x+2,y,scale,true,true,true,false))
        assert(E.pointer(view,x+12,y+15,scale,true,false,true,false))
        assert(not P.edits.dirty) -- preview, not committed per frame
        E.pointer(view,x+12,y+15,scale,true,false,false,true)
        for _,s in ipairs(m.stops) do assert(math.abs(P.stops[s.id].x-x-10)<.001) end
        assert(#P.markers(view,P.filters())==1) -- both services still share a dock
        D.undo(P.edits);P.refresh();assert(not P.edits.dirty)
        E.pointer(view,x,y,scale,true,true,true,false)
        E.pointer(view,x+30,y+30,scale,false,false,false,true)
        assert(not P.edits.dirty) -- release outside cancels
        E.selected=id;E.tool='place'
        E.pointer(view,80,90,scale,true,true,true,false)
        E.pointer(view,80,90,scale,true,false,false,true)
        assert(P.stops[id].map=='mhaura' and P.stops[id].x==80)
        """)

    def test_save_reload_backup_invalid_and_shipping_validation(self):
        with tempfile.TemporaryDirectory(prefix='_poi_tmp_',dir=ADDON/'tests') as temp:
            path=Path(temp)/'poi-corrections.json';self.lua.globals().path=path.as_posix()
            self.lua.execute("""
            E.place({level='zone',key='west'},{P.stops[id]},123.25,245.5)
            assert(D.save(P.edits,path,P.base,C,W))
            E.place({level='world'},{P.stops[id]},3210,4567)
            assert(D.save(P.edits,path,P.base,C,W))
            local loaded=D.new();assert(D.load(loaded,path,P.base,C,W))
            assert(loaded.changes.stops[id].x==123.25 and loaded.changes.world[id].y==4567)
            """)
            spec=importlib.util.spec_from_file_location('import_poi',ADDON/'tools/import_poi_corrections.py')
            importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
            doc=json.loads(path.read_text());validated=importer.validate(doc)
            self.assertEqual(validated['stops']['outpost-ronfaure']['x'],123.25)
            output,report=importer.B.build(corrections_path=path,write_outputs=False)
            stop=next(s for s in output['stops'] if s['id']=='outpost-ronfaure')
            self.assertEqual((stop['map'],stop['x'],stop['y']),('west',123.25,245.5))
            self.assertEqual(output['hubs']['outpost-ronfaure']['world'],[3210,4567])
            self.assertIn('corrections_sha256',report)
            self.assertTrue(Path(str(path)+'.bak').exists())
            doc['changes']['stops']['made-up-poi']={'hidden':True}
            with self.assertRaises(Exception):importer.validate(doc)
            path.write_text('broken');Path(str(path)+'.bak').write_text('broken')
            self.lua.execute("local bad=D.new();assert(not D.load(bad,path,P.base,C,W));assert(not D.save(bad,path,P.base,C,W))")
            self.assertEqual(path.read_text(),'broken')

    def test_invalid_coordinates_and_hidden_transport(self):
        self.lua.execute("""
        for _,p in ipairs({{map='west',x=0/0,y=2},{map='west',x=513,y=2},{map='missing',x=1,y=1},{map='west',x=1}}) do
            local value={schema_version=1,changes={world={},stops={[id]=p}}}
            assert(not pcall(D.validate,value,P.base,C,W))
        end
        E.selected=P.routes[1].a;local other=P.routes[1].b
        E.hide();assert(#P.links[E.selected]==0 and #P.links[other]==0)
        E.hide();assert(#P.links[E.selected]>0 and #P.links[other]>0)
        """)

if __name__=='__main__':unittest.main()
