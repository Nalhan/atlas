"""Offline source normalization, geometry, provenance and generated-data checks."""
from pathlib import Path
import hashlib
import importlib.util
import json
import unittest
from PIL import Image,ImageChops
from lupa.luajit21 import LuaRuntime

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('horizon_import',ADDON/'tools/import_horizon.py')
importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)

class HorizonImport(unittest.TestCase):
    def test_extract_json_without_running_source_code(self):
        text='throw Error("must not execute");"mapdata/json/maps/204.json":{"name":"West","connections":{}},"next":function(){}'
        self.assertEqual(importer.extract_modules(text),{'204':{'name':'West','connections':{}}})
        with self.assertRaises(ValueError):importer.extract_modules('no JSON modules here')

    def test_coordinate_systems_and_nested_polygons(self):
        self.assertEqual(importer.map_point({},[0,0]),[0,512])
        self.assertEqual(importer.map_point({},[256,256]),[512,0])
        world={'bounds':[[-100,-200],[300,600]]}
        self.assertEqual(importer.map_point(world,[600,-100]),[0,0])
        self.assertEqual(importer.map_point(world,[-200,300]),[512,512])
        outer=[[0,0],[10,0],[10,10],[0,10]]
        inner=[[2,2],[4,2],[4,4],[2,4]]
        self.assertEqual(len(importer.rings([[outer],[inner]])),2)
        self.assertFalse(importer.has_holes([[outer],[inner]]))
        self.assertTrue(importer.has_holes([outer,inner]))
        self.assertTrue(importer.point_inside(outer,[5,5]))
        self.assertFalse(importer.point_inside(outer,[20,20]))

    def test_server_parser_retains_direction_and_xyz(self):
        text='''music:
  day: 1
zonelines:
  z2s0:
    from: [-1, -2, 3]
    to: east_ronfaure
    at: [10, 20, 30, 1.5]
    scale: [1, 5]
other:
  zbad:
    from: [99,99,99]
'''
        rows=importer.parse_server(text)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['from'],[-1,-2,3])
        self.assertEqual(rows[0]['at'],[10,20,30,1.5])

    def test_published_shapes_only_bind_existing_allowed_directions(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        lua.execute('''
        local C=require('src.catalog');local H=require('src.hotspots')
        local data=require('data.wiki_hotspots');local total=0;local exercised=false
        for map,entries in pairs(data) do for id,record in pairs(entries) do
            local exit
            for _,e in ipairs(C.exits(map)) do if e.id==id then exit=e end end
            assert(exit and exit.target.map==record.target_map)
            for _,poly in ipairs(record.polygons) do
                assert(#poly>=3)
                for _,pt in ipairs(poly) do
                    assert(pt[1]>=0 and pt[1]<=512 and pt[2]>=0 and pt[2]<=512)
                    if not exercised and not H.contains(H.default(exit),pt[1],pt[2]) then
                        local store=H.new();local hits=H.hits(store,map,{exit},pt[1],pt[2])
                        assert(#hits==1) -- imported label area beyond the entrance
                        H.set(store,map,id,{0,0,4,4})
                        assert(#H.hits(store,map,{exit},pt[1],pt[2])==0)
                        H.undo(store);assert(#H.hits(store,map,{exit},pt[1],pt[2])==1)
                        exercised=true
                    end
                end
            end
            total=total+1
        end end
        assert(exercised and total>0)
        ''')
        report=importer.read(importer.DATA/'report.json')
        published=importer.read(importer.DATA/'published-hotspots.json')
        self.assertEqual(report['published_endpoint_areas'],sum(len(v) for v in published['areas'].values()))
        self.assertEqual(importer.sha(ADDON/'data/catalog.lua'),report['runtime_connectivity_sha256'])
        self.assertFalse(report['runtime_connectivity_changed'])
        records=importer.read(importer.DATA/'candidates.json')['server']
        self.assertTrue(all(r['direction']=='a_to_b' and r['publication']=='candidate_only' for r in records))
        for r in records:
            for key in ('exit','arrival'):
                if r[key] is not None:self.assertTrue(all(0<=n<=512 for n in r[key]))

    def test_regional_art_uses_bounded_native_level_five_pages(self):
        source=importer.read(importer.ASSETS/'SOURCES.json')
        self.assertEqual((source['zoom_level'],source['texture_size']),(5,1024))
        builder=importer.regional_builder()
        tiles={}
        for row in source['source_files']:
            path=ADDON/row['path']
            self.assertEqual(importer.sha(path),row['sha256'])
            coords=tuple(map(int,path.stem.split('-')))
            tiles[coords]=Image.open(path).convert('RGB')
        runtime=LuaRuntime(unpack_returned_tuples=True)
        runtime.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        boards=runtime.eval("require('data.regional_art')")
        total=0
        for region,board in boards.items():
            crop=list(board['artwork']['source_bounds'].values())
            pages=list(board['artwork']['pages'].values())
            expected={(x,y) for y in range(0,int(board['height']),1024) for x in range(0,int(board['width']),1024)}
            self.assertEqual({(int(page['x']),int(page['y'])) for page in pages},expected)
            self.assertEqual(sum(page['w']*page['h'] for page in pages),board['width']*board['height'])
            for page in pages:
                path=ADDON/page['path'];total+=1
                self.assertEqual(importer.sha(path),source['assets'][page['path']])
                image=Image.open(path).convert('RGB');self.assertEqual(image.size,(1024,1024))
                x,y,w,h=(int(page[field]) for field in ('x','y','w','h'))
                native=builder.crop_tiles((crop[0]+x,crop[1]+y,crop[0]+x+w,crop[1]+y+h),tiles)
                self.assertIsNone(ImageChops.difference(native,image.crop((0,0,w,h))).getbbox())
        self.assertEqual(total,len(source['assets']))
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('package.path=... .. "/?.lua;" .. package.path',ADDON.as_posix())
        lua.execute('''
        local R=require('src.regions');local C=require('src.catalog')
        for _,id in ipairs(R.order) do
            local b=R.get(id);assert(b.artwork.zoom_level==5)
            assert(b.artwork.source_bounds[3]-b.artwork.source_bounds[1]==b.width)
            assert(b.artwork.source_bounds[4]-b.artwork.source_bounds[2]==b.height)
            for _,key in ipairs(b.order) do
                local n=b.nodes[key]
                assert(n.x-n.w/2>=0 and n.x+n.w/2<=b.width)
                assert(n.y-n.h/2>=0 and n.y+n.h/2<=b.height)
                for _,map in ipairs(n.maps) do assert(C.maps[map] and b.by_map[map]==key) end
            end
        end
        ''')

if __name__=='__main__':unittest.main()
