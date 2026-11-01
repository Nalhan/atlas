from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'tools/antigravity_trial.py'
spec=importlib.util.spec_from_file_location('antigravity_trial',path)
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)

class TrialChecks(unittest.TestCase):
    def test_assignment_avoids_greedy_pair_swap(self):
        self.assertEqual(set(trial.minimum_assignment([[1,2],[2,100]])),{(0,1),(1,0)})
    def test_more_candidates_and_more_references(self):
        self.assertEqual(set(trial.minimum_assignment([[5,1,0],[0,9,10]])),{(0,2),(1,0)})
        self.assertEqual(set(trial.minimum_assignment([[5,0],[1,9],[0,10]])),{(0,1),(2,0)})
        self.assertEqual(trial.minimum_assignment([]),[])
    def test_schema_avoids_provider_numeric_enum_failure(self):
        value=trial.schema('test')
        self.assertNotIn('enum',value['properties']['schema_version'])
        self.assertEqual(value['properties']['schema_version']['minimum'],1)
        self.assertFalse(value['additionalProperties'])

    def test_resumed_json_and_stream_result_parsing(self):
        with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=path.parents[1]/'tests') as temp:
            log=Path(temp)/'events.ndjson'
            result={'status':'SUCCESS','response':'{}','usage':{'total_tokens':123}}
            log.write_text(json.dumps(result,indent=2),encoding='utf-8')
            self.assertEqual(trial.parse_run(log)[1],result)
            log.write_text(json.dumps({'event':'step'})+'\n'+json.dumps({'event':'result','result':result})+'\n',encoding='utf-8')
            events,parsed=trial.parse_run(log)
            self.assertEqual(len(events),2)
            self.assertEqual(parsed,result)

    def test_novel_reviews_reject_changed_candidates_and_missing_decisions(self):
        job='zulkheim'
        doc=trial.read(trial.EXPERIMENT/'candidates'/f'{job}.json')
        review=trial.read(trial.EXPERIMENT/'reviews'/f'{job}_novel.json')
        unmatched=[d['id'] for d in review['decisions']]
        manifest=trial.read(trial.DATA/'manifest.json')
        summary=trial.novel_review(job,doc,unmatched,manifest)
        self.assertEqual((summary['accept'],summary['needs_work']),(5,1))
        original_sha=trial.sha
        with patch.object(trial,'sha',side_effect=lambda p:'changed' if Path(p).name==f'{job}.json' else original_sha(p)):
            with self.assertRaisesRegex(ValueError,'candidate fingerprint'):
                trial.novel_review(job,doc,unmatched,manifest)
        with self.assertRaisesRegex(ValueError,'coverage mismatch'):
            trial.novel_review(job,doc,unmatched[:-1],manifest)

    def test_success_without_annotation_is_incomplete(self):
        for response in ('', '{}', 'Here is my plan.'):
            self.assertIsNone(trial.annotation_output({'status':'SUCCESS','response':response},'zulkheim'))
        value=trial.read(trial.EXPERIMENT/'candidates/zulkheim.json')
        self.assertEqual(trial.annotation_output({'structured_output':value},'zulkheim'),value)
        self.assertEqual(trial.annotation_output({'response':'```json\n'+json.dumps(value)+'\n```'},'zulkheim'),value)
        self.assertIsNone(trial.annotation_output({'structured_output':value},'north_east'))

if __name__=='__main__':unittest.main()
