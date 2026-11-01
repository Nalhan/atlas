"""Checks the annotation publication gates without changing real candidates/reviews."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('annotation_tools',ADDON/'tools/annotations.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

class AnnotationGates(unittest.TestCase):
    def setUp(self):
        self.real=pipeline.DATA
        self.manifest=pipeline.read(self.real/'manifest.json')
        self.candidate=copy.deepcopy(pipeline.read(self.real/'candidates/zulkheim.json')['passages'][0])

    def test_invalid_geometry_and_self_approval(self):
        for invalid in ([float('nan'),2],[-1,2],[513,2],[True,2],['10',2]):
            p=copy.deepcopy(self.candidate);p['a']['exit']=invalid
            with self.assertRaises(ValueError):pipeline.validate_passage(p,self.manifest['maps'],'test')
        p=copy.deepcopy(self.candidate);p['status']='reviewed'
        with self.assertRaises(ValueError):pipeline.validate_passage(p,self.manifest['maps'],'test')
        p=copy.deepcopy(self.candidate);p['b']['map']='invented_floor'
        with self.assertRaises(ValueError):pipeline.validate_passage(p,self.manifest['maps'],'test')

    def test_stale_reviews_and_missing_independent_coverage(self):
        with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=ADDON/'tests') as temp:
            temp=Path(temp)
            self.assertEqual(temp.resolve().parent,(ADDON/'tests').resolve())
            pipeline.write(temp/'manifest.json',self.manifest)
            review=pipeline.read(self.real/'reviews/decisions.json')
            for job in self.manifest['jobs']:
                doc=pipeline.read(self.real/'candidates'/f'{job}.json')
                for p in doc['passages']:
                    for e in p['evidence']:
                        if e['kind']=='artwork':e['source']=str(self.real/e['source'])
                pipeline.write(temp/'candidates'/f'{job}.json',doc)
            for d in review['decisions']:
                for e in d.get('evidence',[]):
                    if e['kind']=='artwork':e['source']=str(self.real/e['source'])
            review['packet_sha256']={e['source']:hashlib.sha256(Path(e['source']).read_bytes()).hexdigest()
                for d in review['decisions'] if d['decision']=='accept' for e in d['evidence'] if e['kind']=='artwork'}
            review['manifest_sha256']=hashlib.sha256((temp/'manifest.json').read_bytes()).hexdigest()
            hashes={job:hashlib.sha256((temp/'candidates'/f'{job}.json').read_bytes()).hexdigest() for job in self.manifest['jobs']}
            review['candidate_sha256']=hashes
            independent=pipeline.read(self.real/'reviews/independent_inventory.json')
            pipeline.write(temp/'reviews/independent_inventory.json',independent)
            review['independent_inventory_sha256']=hashlib.sha256((temp/'reviews/independent_inventory.json').read_bytes()).hexdigest()
            pipeline.write(temp/'reviews/decisions.json',review)
            pipeline.DATA=temp
            try:
                *_,stats=pipeline.collect();self.assertEqual(stats['pending'],0)
                altered=copy.deepcopy(review);altered['candidate_sha256']['zulkheim']='stale'
                pipeline.write(temp/'reviews/decisions.json',altered)
                with self.assertRaisesRegex(ValueError,'stale'):pipeline.collect()
                altered=copy.deepcopy(review);altered['manifest_sha256']='stale'
                pipeline.write(temp/'reviews/decisions.json',altered)
                with self.assertRaisesRegex(ValueError,'manifest changed'):pipeline.collect()
                altered=copy.deepcopy(review);altered['packet_sha256'][next(iter(altered['packet_sha256']))]='stale'
                pipeline.write(temp/'reviews/decisions.json',altered)
                with self.assertRaisesRegex(ValueError,'artwork changed'):pipeline.collect()
                altered=copy.deepcopy(review);altered['reviewer']='Codex'
                pipeline.write(temp/'reviews/decisions.json',altered)
                with self.assertRaisesRegex(ValueError,'own batch'):pipeline.collect()
                pipeline.write(temp/'reviews/decisions.json',review)
                independent['inventory']=independent['inventory'][:-1]
                pipeline.write(temp/'reviews/independent_inventory.json',independent)
                review['independent_inventory_sha256']=hashlib.sha256((temp/'reviews/independent_inventory.json').read_bytes()).hexdigest()
                pipeline.write(temp/'reviews/decisions.json',review)
                with self.assertRaisesRegex(ValueError,'misses pilot'):pipeline.collect()
            finally:pipeline.DATA=self.real

    def test_runtime_build_provenance(self):
        manifest,jobs,review,accepted,stats=pipeline.collect()
        build=pipeline.read(self.real/'build.json')
        self.assertEqual(build['candidate_sha256'],{job:v[1] for job,v in jobs.items()})
        self.assertEqual(build['runtime_sha256'],hashlib.sha256((ADDON/'data/catalog.lua').read_bytes()).hexdigest())
        self.assertEqual(build['regions_sha256'],hashlib.sha256((ADDON/'data/regions.lua').read_bytes()).hexdigest())
        self.assertEqual(stats['accepted'],len(accepted))
        self.assertFalse(review['traversal_verified'])

if __name__=='__main__':unittest.main()
