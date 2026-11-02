"""Independent native inventory, Besieged geometry and transport checks."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct
import unittest
from unittest.mock import patch
from PIL import Image,ImageChops

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('aht_build',ADDON/'tools/expand_aht_urhgan.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
def read(path):return json.loads((ADDON/path).read_text())

class AhtUrhgan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua=A.P.runtime();cls.data=A.P.plain(cls.lua.eval("require('data.aht_urhgan')"))
        cls.world=A.P.plain(cls.lua.eval("require('data.world_art')"))

    def test_all_original_native_maps_are_accounted_for(self):
        dll,base=A.P.native_table();expected=set();zones=set(sum(A.CORE.values(),[]))
        binary=A.P.runtime(True);wrap=binary.eval(b"require('src.dat_image').wrap")
        for index in range(294,432):
            zone,floor=struct.unpack_from('<HB',dll,base+index*14)
            if zone not in zones:continue
            definition=A.P.native_map(dll,base,'test',zone,floor,index,'test','test')
            try:A.E.original(definition,wrap)
            except ValueError:continue
            expected.add((zone,floor,index))
        actual={(d['zone'],d['floor'],d['index']) for d in self.data['maps'] if 'index' in d}
        self.assertEqual(actual,expected)
        self.assertEqual(zones,{d['zone'] for d in self.data['maps']})
        self.assertEqual(len({d['key'] for d in self.data['maps']}),len(self.data['maps']))

    def test_besieged_identity_and_nonoverlapping_sheet(self):
        sheet=self.world['besieged'];manifest=read('assets/world/SOURCES.json')['besieged']
        raw=(A.P.ROOT/'SquareEnix/FINAL FANTASY XI'/manifest['path']).read_bytes()
        self.assertIn(b'm_ex3_rg',raw[49:65]);self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest['sha256'])
        self.assertEqual(sheet['dat'],53416);self.assertGreaterEqual(sheet['x'],8192)
        self.assertGreaterEqual(self.world['width'],sheet['x']+sheet['w'])
        for d in self.data['maps']:
            nodes=[n for n in self.world['zones'] if d['key'] in n['maps']]
            self.assertEqual(len(nodes),1,d['key'])
            b=nodes[0]['bounds'];self.assertTrue(sheet['x']<=b[0]<b[2]<=sheet['x']+sheet['w'])
            self.assertTrue(sheet['y']<=b[1]<b[3]<=sheet['y']+sheet['h'])

    def test_reference_art_is_explicit_and_never_claims_native_positions(self):
        refs=[d for d in self.data['maps'] if d.get('reference_only')]
        meta=read('annotations/imports/horizon/map-metadata.json')
        for d in refs:
            self.assertNotIn('index',d);self.assertNotIn('dat',d)
            self.assertIsNone(self.lua.eval("require('src.catalog').find_player_map")(d['zone'],d['floor']))
            original=ADDON/f"annotations/aht-urhgan/wiki-images/{d['wiki_map']}-{meta[str(d['wiki_map'])]['filename']}"
            expected=Image.open(original).convert('RGB').resize((512,512),Image.Resampling.LANCZOS)
            actual=Image.open(ADDON/d['asset']).convert('RGB')
            self.assertIsNone(ImageChops.difference(expected,actual).getbbox())
        self.assertEqual(len(refs),9)

    def test_links_keep_ferries_separate_and_shared_docks_reachable(self):
        self.lua.execute('''
        local C=require('src.catalog');local P=require('src.pois');local f=P.filters()
        local docks=P.markers({level='zone',key='mhaura'},f)
        assert(#docks==1 and #docks[1].stops==2)
        local targets={}
        for _,stop in ipairs(docks[1].stops) do targets[P.links[stop.id][1].target.area]=true end
        assert(targets.Selbina and targets['Aht Urhgan Whitegate'])
        for _,passage in ipairs(require('data.aht_urhgan').passages) do
            local a,b=C.maps[passage.a.map].zone,C.maps[passage.b.map].zone
            assert(not ((a==50 and (b==249 or b==53)) or (b==50 and (a==249 or a==53))))
            if (a==50 and b==52) or (b==50 and a==52) then assert(passage.kind=='runic_portal' and passage.note~='') end
        end
        ''')
        report=read('annotations/aht-urhgan/floor-matches.json')
        whitegate=next(r for r in report['matches'] if r['zone']==50)
        self.assertTrue(whitegate['accepted']);self.assertEqual(whitegate['native_map'],'aht_urhgan_whitegate_f0')
        self.assertLess(whitegate['server_geometry'][0]['mean_error'],8)
        self.assertGreater(whitegate['server_geometry'][1]['mean_error'],32)

    def test_offline_build_preserves_outputs_and_prior_catalog(self):
        paths=['data/catalog.lua','data/expansion.lua','data/aht_urhgan.lua','data/aht_regions.lua',
            'data/aht_hotspots.lua','annotations/aht-urhgan/build.json','assets/references/SOURCES.json']
        def hashes():return {path:hashlib.sha256((ADDON/path).read_bytes()).hexdigest() for path in paths}
        before=hashes()
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline build accessed network')):A.build()
        self.assertEqual(before,hashes())

if __name__=='__main__':unittest.main()
