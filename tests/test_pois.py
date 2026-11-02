"""Transport graph, native coordinates, filtering and navigation/provenance."""
from pathlib import Path
import hashlib
import importlib.util
import json
import unittest
from unittest.mock import patch

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_pois',ADDON/'tools/build_pois.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def sha(path):return hashlib.sha256((ADDON/path).read_bytes()).hexdigest()

class PointsOfInterest(unittest.TestCase):
    def test_filters_clustering_and_graph(self):
        lua=builder.P.runtime()
        lua.execute('''
        local P=require('src.pois');local C=require('src.catalog');local f=P.filters()
        assert(#P.markers({level='world'},f)==35)
        assert(#P.markers({level='world',world_legacy=true},f)==0)
        assert(#P.markers({level='zone',key='port_jeuno'},f)==4)
        assert(#P.markers({level='zone',key='selbina'},f)==1)
        assert(#P.markers({level='zone',key='xarcabard'},f)==2)
        assert(#P.markers({level='zone',key='latheine'},f)==1)
        assert(#P.markers({level='zone',key='west'},f)==1)
        assert(#P.markers({level='zone',key='bibiki_bay_f1'},f)==1)
        assert(#P.markers({level='zone',key='bibiki_bay_f2'},f)==1)
        assert(#P.markers({level='zone',key='north'},f)==0)
        f.boat[1]=false;assert(#P.markers({level='world'},f)==29)
        assert(#P.markers({level='zone',key='selbina'},f)==0)
        f.airship[1]=false;assert(#P.markers({level='world'},f)==24)
        f.outpost[1]=false;assert(#P.markers({level='world'},f)==6)
        assert(#P.markers({level='zone',key='xarcabard'},f)==1)
        f.teleport[1]=false;assert(#P.markers({level='world'},f)==0)
        assert(#P.markers({level='zone',key='xarcabard'},f)==0)
        for _,r in ipairs(P.routes) do
            assert(P.stops[r.a] and P.stops[r.b] and r.requirement~='')
            assert(P.links[r.a][1].target.id==r.b and P.links[r.b][1].target.id==r.a)
            assert(P.stops[r.a].category==r.category and P.stops[r.b].category==r.category)
            for _,passage in ipairs(C.passages) do assert(passage.id~=r.id) end
        end
        ''')

    def test_native_projection_matches_cached_wiki_game_coordinates(self):
        lua=builder.P.runtime();data=builder.P.plain(lua.eval("require('data.pois')"))
        maps=builder.P.plain(lua.eval("require('src.catalog')"))['maps']
        seed=json.loads((ADDON/'annotations/poi/transport.json').read_text())
        path=ADDON/'annotations/poi/corrections.json'
        corrections=json.loads(path.read_text())['changes'] if path.exists() else {'world':{},'stops':{}}
        metadata=builder.W.extract_modules((builder.W.DATA/'ffximap.js').read_text())
        dll,base=builder.P.native_table()
        for route,runtime in zip(seed['routes'],data['routes']):
            for side,other in [('a','b'),('b','a')]:
                stop=next(s for s in data['stops'] if s['id']==runtime[side])
                if not stop.get('map'):continue
                m=maps[stop['map']]
                n=builder.P.native_map(dll,base,m['key'],m['zone'],m['floor'],m['index'],m['name'],m['region'])
                info=metadata[route['wiki_'+side]];target=route['wiki_'+other]
                records=[r for k,r in info['connections'].items() if k==target or int(target) in r.get('links',[])]
                self.assertEqual(len(records),1);pulse=records[0]['pulse']
                self.assertEqual(len(pulse),1)
                lat,lng=pulse[0];t=n['transform'];f=abs(t['scale'])/5
                expected=[lng*f-t['offset_x'],-lat*f-t['offset_y']] if info.get('bounds') else [lng*2,512-lat*2]
                self.assertAlmostEqual(stop['x'],expected[0],places=2)
                self.assertAlmostEqual(stop['y'],expected[1],places=2)
                self.assertTrue(0<=stop['x']<=512 and 0<=stop['y']<=512)
        for pt in seed.get('points',[]):
            stop=next(s for s in data['stops'] if s['id']==pt['id'])
            m=maps[stop['map']]
            n=builder.P.native_map(dll,base,m['key'],m['zone'],m['floor'],m['index'],m['name'],m['region'])
            t=n['transform'];f=abs(t['scale'])/5
            if pt.get('entity'):
                matches=[e for e in metadata[pt['wiki_map']].get('entities',[]) if e[1]==pt['entity']]
                self.assertEqual(len(matches),1)
                gx,gz=matches[0][2],matches[0][4]
            else:
                gx,gz=pt['world_xy']
            correction=corrections['stops'].get(pt['id'],{})
            expected=[correction['x'],correction['y']] if 'map' in correction else [gx*f-t['offset_x'],-gz*f-t['offset_y']]
            self.assertAlmostEqual(stop['x'],expected[0],places=2)
            self.assertAlmostEqual(stop['y'],expected[1],places=2)
            if 'map' in correction:self.assertEqual(stop['map'],correction['map'])
            self.assertTrue(0<=stop['x']<=512 and 0<=stop['y']<=512)
        for hub,point in corrections['world'].items():
            self.assertEqual(data['hubs'][hub]['world'],[point['x'],point['y']])

    def test_visit_uncharted_hub_and_history(self):
        lua=builder.P.runtime()
        lua.execute('''
        local P=require('src.pois');local N=require('src.navigation');local state=N.new()
        for id,stop in pairs(P.stops) do
            N.go(state,'zone','west');local before=state.current
            P.visit(state,id)
            if stop.map then
                assert(state.current.level=='zone' and state.current.key==stop.map)
                assert(state.current.cx==stop.x and state.current.cy==stop.y)
                assert(state.current.arrival.poi==id)
            else
                assert(state.current.level=='world' and state.current.focus and not state.current.initialized)
                local b=state.current.focus;local w=P.hubs[stop.hub].world
                assert((b[1]+b[3])/2==w[1] and (b[2]+b[4])/2==w[2])
                assert(state.current.poi_focus==id)
            end
            N.back(state);assert(state.current==before)
            N.forward(state);assert(state.current~=before)
        end
        ''')

    def test_offline_build_is_repeatable_and_does_not_change_passages(self):
        paths=['data/pois.lua','annotations/poi/build.json','data/catalog.lua','data/expansion.lua']
        before={path:sha(path) for path in paths}
        with patch('urllib.request.urlopen',side_effect=AssertionError('Build accessed the network')):builder.build()
        self.assertEqual(before,{path:sha(path) for path in paths})

if __name__=='__main__':unittest.main()
