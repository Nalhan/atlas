"""Check deterministic source correlation, held cases and append-only publication."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import unittest
from unittest.mock import patch

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('expand_regions',ADDON/'tools/expand_regions.py')
expand=importlib.util.module_from_spec(spec);spec.loader.exec_module(expand)
def read(path):return json.loads((ADDON/path).read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256((ADDON/path).read_bytes()).hexdigest()
def distance(a,b):return math.hypot(a['x']-b['x'],a['y']-b['y'])

class Expansion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lua=expand.P.runtime()
        cls.base=expand.P.plain(lua.eval("require('data.catalog')"))
        cls.extra=expand.P.plain(lua.eval("require('data.expansion')"))
        cls.maps={m['key']:m for m in cls.base['maps']+cls.extra['maps']}
        cls.review=read('annotations/expansion/connection-review.json')

    def test_fingerprints_and_floor_confidence(self):
        summary=read('annotations/expansion/build.json');source=read('annotations/expansion/sources.json')
        self.assertEqual(digest('data/catalog.lua'),summary['base_catalog_sha256'])
        self.assertEqual(digest('data/expansion.lua'),summary['generated_sha256'])
        for row in source['files']:self.assertEqual(digest(row['path']),row['sha256'])
        seen=set()
        for m in self.maps.values():
            identity=(m['zone'],m.get('floor'));self.assertNotIn(identity,seen);seen.add(identity)
        floors=read('annotations/expansion/floor-matches.json')
        for row in floors['matches']:
            if row['accepted'] and len(row['candidate_scores'])>1:
                self.assertGreaterEqual(row['score'],.20)
                self.assertGreaterEqual(row['floor_margin'],.035)
                self.assertGreaterEqual(row['image_margin'],.035)
        self.assertTrue(floors['held'])
        self.assertFalse(summary['traversal_verified'])

    def test_reciprocal_evidence_and_independent_arrival_focus(self):
        directed={r['id']:r for r in self.review['directed_candidates']}
        self.assertEqual(self.extra['passages'],self.review['published'])
        for p in self.extra['passages']:
            r,s=[directed[key] for key in p['source_ids']]
            self.assertEqual((r['a'],r['b']),(s['b'],s['a']))
            for a,b in [(r['exit'],s['arrival']),(r['arrival'],s['exit'])]:
                self.assertLessEqual(math.dist(a,b),24)
            for e in (p['a'],p['b']):
                self.assertIn(e['map'],self.maps)
                for field in ('x','y','arrival_x','arrival_y'):
                    self.assertTrue(0<=e[field]<=512)
            # Arrival focus comes from the opposite source record, rather than
            # borrowing its source mouth coordinate.
            self.assertEqual([p['a']['arrival_x'],p['a']['arrival_y']],s['arrival'])
            self.assertEqual([p['b']['arrival_x'],p['b']['arrival_y']],r['arrival'])

    def test_no_transport_duplicates_or_reversed_curated_drops(self):
        def city(zone):
            for name,ids in [('sandoria',range(230,234)),('bastok',range(234,238)),('windurst',range(238,242)),('jeuno',range(243,247)),('kazham',[250])]:
                if zone in ids:return name
        for p in self.extra['passages']:
            za,zb=[self.maps[p[e]['map']]['zone'] for e in ('a','b')]
            if city(za) and city(zb):self.assertEqual(city(za),city(zb))
            for old in self.base['passages']:
                if old.get('one_way'):
                    self.assertNotEqual((za,zb),(self.maps[old['b']['map']]['zone'],self.maps[old['a']['map']]['zone']))
            for q in self.extra['passages']:
                if p['id']==q['id'] or p['source_method']==q['source_method']:continue
                for a,b in [(q['a'],q['b']),(q['b'],q['a'])]:
                    if (a['map'],b['map'])==(p['a']['map'],p['b']['map']):
                        self.assertFalse(distance(a,p['a'])<=32 and distance(b,p['b'])<=32)

    def test_new_regions_are_reachable_and_wiki_fallback_is_retained(self):
        edges={k:set() for k in self.maps}
        for p in self.base['passages']+self.extra['passages']:
            a,b=p['a']['map'],p['b']['map'];edges[a].add(b)
            if not p.get('one_way'):edges[b].add(a)
        seen={'west','kazham'};pending=['west','kazham']
        while pending:
            for key in edges[pending.pop()]-seen:seen.add(key);pending.append(key)
        self.assertTrue(set(expand.CORE)<=set(self.maps[k]['region'] for k in seen))
        self.assertIn('port_jeuno',seen)
        self.assertTrue(any({p['a']['map'],p['b']['map']}=={'lower_jeuno','port_jeuno'}
            and p['source_method']=='wiki_reciprocal' for p in self.extra['passages']))

    def test_offline_rebuild_is_repeatable_and_preserves_base(self):
        paths=['data/catalog.lua','data/regions.lua','data/expansion.lua','data/expanded_hotspots.lua',
            'data/expanded_regions.lua','annotations/expansion/build.json']
        before={path:digest(path) for path in paths}
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline build accessed network')):expand.build()
        self.assertEqual(before,{path:digest(path) for path in paths})

if __name__=='__main__':unittest.main()
