"""World selector geometry, native canvas coordinates and portable edits."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]

class WorldSelectors(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for path in [ADDON,ADDON.parent/'libs']:
            self.lua.execute("package.path=... .. '/?.lua;' .. package.path",path.as_posix())
        self.lua.execute("""
        T=function(v) return v end
        S=require('src.world_selectors');E=require('src.world_selector_editor');W=require('src.world')
        E.selected='zone-100'
        function measure(t) return #t*7,14 end
        """)

    def test_drag_resize_draw_and_cancel(self):
        self.lua.execute("""
        local node=E.selected_node();local r=S.bounds(node,2,measure)
        local x,y=(r[1]+r[3])/2,(r[2]+r[4])/2
        E.pointer(x,y,2,measure,true,true,true,false)
        E.pointer(x+20,y+30,2,measure,true,false,true,false)
        assert(not S.store.dirty)
        E.pointer(x+20,y+30,2,measure,true,false,false,true)
        local moved=S.node(E.selected).bounds;assert(moved[1]==r[1]+20 and moved[2]==r[2]+30)
        E.pointer(moved[3],moved[4],2,measure,true,true,true,false)
        E.pointer(moved[3]+30,moved[4]+40,2,measure,true,false,false,true)
        assert(S.node(E.selected).bounds[3]==moved[3]+30)
        S.undo();assert(S.node(E.selected).bounds[3]==moved[3])
        S.undo();assert(not S.store.dirty)
        E.tool='draw';E.pointer(1000,2000,2,measure,true,true,true,false)
        E.pointer(1200,2100,2,measure,true,false,false,true)
        assert(S.node(E.selected).bounds[1]==1000)
        local bounds=W.zone_bounds('west');assert((bounds[1]+bounds[3])/2==1100)
        S.undo();E.pointer(x,y,2,measure,true,true,true,false)
        E.pointer(x+50,y+50,2,measure,false,false,false,true)
        assert(not S.store.dirty) -- release outside does not commit
        """)

    def test_besieged_dynamic_default_and_manual_bounds(self):
        self.lua.execute("""
        local node=S.node('zone-50');local r=S.bounds(node,1,measure);local r2=S.bounds(node,2,measure)
        assert(math.abs((r[3]-r[1])-2*(r2[3]-r2[1]))<.001)
        assert(S.set('zone-50',{11000,6000,11500,6200}))
        local actual=S.bounds(S.node('zone-50'),3,measure)
        assert(actual[1]==11000 and actual[4]==6200 and S.node('zone-50').custom_bounds)
        S.set('zone-50',nil);assert(not S.store.dirty)
        assert(not S.set('zone-50',{0,0,1,1}))
        for _,rect in ipairs({{0,0,0/0,10},{0,0,13000,10},{-1,0,10,10}}) do
            assert(not pcall(S.validate,{schema_version=1,kind='world_selectors',selectors={['zone-50']=rect}},S.base))
        end
        """)

    def test_persistence_backup_and_shipping_validation(self):
        with tempfile.TemporaryDirectory(prefix='_selector_tmp_',dir=ADDON/'tests') as folder:
            path=Path(folder)/'world-selectors.json';self.lua.globals().path=path.as_posix()
            self.lua.execute("""
            assert(S.set('zone-100',{2000,3000,2300,3100}));assert(S.save(path))
            S.set('zone-50',{11000,6000,11500,6200});assert(S.save(path))
            S.store={changes={},saved={},undo={}};assert(S.load(path));assert(not S.store.dirty)
            assert(S.node('zone-100').bounds[1]==2000 and S.node('zone-50').bounds[1]==11000)
            """)
            spec=importlib.util.spec_from_file_location('selectors_import',ADDON/'tools/import_world_selectors.py')
            importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
            document=json.loads(path.read_text());self.assertEqual(importer.validate(document)['zone-100'],[2000,3000,2300,3100])
            document['selectors']['zone-made-up']=[0,0,10,10]
            with self.assertRaises(Exception):importer.validate(document)
            path.write_text('bad')
            self.lua.execute("assert(S.load(path));assert(S.node('zone-100').bounds[1]==2000)")
            Path(str(path)+'.bak').write_text('bad')
            self.lua.execute("assert(not S.load(path));assert(not S.save(path))")
            self.assertEqual(path.read_text(),'bad')

if __name__=='__main__':unittest.main()
