import unittest,torch,json
from exps.paper2_docred_formal.run import simple_parse,simple_request
from exps.paper2_docred_formal.analyze import paired,holm
from exps.paper2_docred_v2.test_contracts import fixture

class FormalChecks(unittest.TestCase):
    def test_failed_gate_blocks_expansion_before_data_access(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from exps.paper2_docred_formal import run
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'pilot_results.json').write_text('{"gate_passed":false}')
            with patch.object(run,'SOURCE',folder),patch.object(run,'prepare') as prepare:
                with self.assertRaises(AssertionError):run.freeze()
                prepare.assert_not_called()
    def test_invalid_response_does_not_destroy_graph(self):
        r,_=fixture()
        for raw in ['', '{"keep_record_ids":["unknown"]}', '{"keep_record_ids":["r","r"]}']:
            selected,status=simple_parse(raw,r);self.assertEqual(selected,r);self.assertEqual(status,'parse_failure_no_edit')
    def test_empty_output_is_deferred_to_episode_guard(self):
        r,_=fixture();self.assertEqual(simple_parse('{"keep_record_ids":[]}',r),([], 'ok'))
    def test_only_given_records(self):
        r,_=fixture();out,status=simple_parse('```json\n{"keep_record_ids":["r"]}\n```',r);self.assertEqual(out,[r[0]])
    def test_statistical_identity_and_holm(self):
        p=paired([.5]*10,[.5]*10);self.assertEqual(p['p'],1);self.assertEqual(p['ci95_pp'],[0.,0.])
        rows=holm([dict(p=x) for x in [.01,.04,.2]]);self.assertEqual([r['p_holm'] for r in rows],[.03,.08,.2])

if __name__=='__main__':unittest.main()
