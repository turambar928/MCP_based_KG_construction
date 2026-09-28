import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_reextraction_control.protocol import ARMS,MODEL,make_prompt,task
from exps.paper1_reextraction_control.scoring import validate_outcome,validate
from exps.paper1_receipt_followup.protocol import filter_response
from exps.paper1_external_receipts.analyze import score_case

ROW={'case_id':'synthetic-only','domain':'receipt','source_evidence':'A SDN BHD TOTAL 10.00',
     'source_lines':['A SDN BHD','TOTAL 10.00'],'required_document_node':'synthetic-only',
     'allowed_relations':['company','date','address','total']}
OLD=[{'head':'synthetic-only','relation':'total','tail':'9.00'}]


class ProtocolTests(unittest.TestCase):
    def test_exactly_four_arms_and_shared_public_inputs(self):
        bodies={a:json.loads(make_prompt(ROW,OLD,a)[1]) for a in ARMS}
        for body in bodies.values():
            body.pop('input_triples',None);body.pop('field_evidence_index',None)
        self.assertTrue(all(v==bodies[ARMS[0]] for v in bodies.values()))
    def test_extraction_has_no_old_graph_or_diagnosis(self):
        changed=[{'head':'private-old-graph','relation':'total','tail':'PRIVATE_SENTINEL'}]
        for arm in ['extract_simple','extract_index']:
            self.assertEqual(make_prompt(ROW,OLD,arm),make_prompt(ROW,changed,arm))
            system,user=make_prompt(ROW,changed,arm)
            self.assertNotIn('input_triples',user);self.assertNotIn('PRIVATE_SENTINEL',system+user)
            self.assertNotIn('diagnostic',user)
    def test_reference_counterfactual_ignored(self):
        extra={**ROW,'reference':OLD,'expected_detection':'fail','gold':'SENTINEL'}
        for a in ARMS:self.assertEqual(make_prompt(ROW,OLD,a),make_prompt(extra,OLD,a))
    def test_index_is_shared_and_no_index_arm_excludes_it(self):
        a=json.loads(make_prompt(ROW,OLD,'repair_index')[1]);b=json.loads(make_prompt(ROW,OLD,'extract_index')[1])
        self.assertEqual(a['field_evidence_index'],b['field_evidence_index'])
        for arm in ['repair_simple','extract_simple']:self.assertNotIn('field_evidence_index',json.loads(make_prompt(ROW,OLD,arm)[1]))
    def test_settings_and_hash(self):
        tasks=[task(ROW,OLD,a) for a in ARMS]
        self.assertEqual(len({t['prompt_sha256'] for t in tasks}),4)
        for t in tasks:self.assertEqual((t['request']['model'],t['request']['temperature'],t['request']['max_tokens']),(MODEL,0,4000))
    def test_mock_outcomes_cannot_enter_formal_scoring(self):
        t=task(ROW,OLD,'extract_index')
        for row in [{'kind':'mock_response','is_mock':True},{'kind':'model_response','is_mock':True}]:
            with self.assertRaises(ValueError):validate_outcome(row,{(t['case_id'],t['arm']):t})
    def fixture(self):
        t=task(ROW,OLD,'extract_index')
        # This in-memory validator fixture is never saved or passed to formal scoring.
        r={'kind':'model_response','is_mock':False,'case_id':t['case_id'],'arm':t['arm'],
           'model':MODEL,'prompt_sha256':t['prompt_sha256'],'status':'ok',
           'raw_response':'{"triples":[]}','triples':[],'attempts':[{'status':'synthetic-unit-test'}],
           'wall_seconds':0.,'usage':{'prompt_tokens':None,'completion_tokens':None}}
        return t,r
    def test_raw_parsed_mismatch_rejected(self):
        t,r=self.fixture();r['triples']=OLD
        with self.assertRaises(ValueError):validate_outcome(r,{(t['case_id'],t['arm']):t})
    def test_model_and_request_mismatch_rejected(self):
        t,r=self.fixture()
        for k,v in [('model','not-permitted'),('prompt_sha256','wrong')]:
            x={**r,k:v}
            with self.assertRaises(ValueError):validate_outcome(x,{(t['case_id'],t['arm']):t})
    def test_all_outcomes_and_unique_ids_required(self):
        t,r=self.fixture()
        with self.assertRaises(ValueError):validate([], [t])
        other=task(ROW,OLD,'repair_index')
        with self.assertRaises(ValueError):validate([r,r],[t,other])
    def test_failure_retained_as_empty(self):
        t,r=self.fixture();r.update(status='transport_error',raw_response='',triples=[])
        self.assertEqual(validate_outcome(r,{(t['case_id'],t['arm']):t}),(t['case_id'],t['arm']))
        ref={'annotated_relations':['total'],'triples':[{'head':'synthetic-only','relation':'total','tail':'10.00'}]}
        self.assertEqual(score_case(OLD,[],ref)['triple_f1'],0.)
    def test_same_response_filter_and_missing_reference_fields(self):
        raw=[{'head':'synthetic-only','relation':'total','tail':'10.00'},
             {'head':'synthetic-only','relation':'date','tail':'NOT_IN_SOURCE'}]
        out,rejected=filter_response(ROW,raw);self.assertEqual(len(out),1);self.assertEqual(len(rejected),1)
        ref={'annotated_relations':['total'],'triples':out}
        self.assertEqual(score_case(OLD,out,ref)['triple_f1'],1.)
    def test_all_sixty_archived_cases(self):
        from exps.paper1_reextraction_control.prepare import read,SOURCE
        rows=read(SOURCE/'inputs.jsonl');graphs={r['case_id']:r['triples'] for r in read(SOURCE/'extraction.jsonl')}
        self.assertEqual(len(rows),60)
        for row in rows:
            bodies={a:json.loads(make_prompt(row,graphs[row['case_id']],a)[1]) for a in ARMS}
            for arm,b in bodies.items():
                if arm.startswith('extract'):self.assertNotIn('input_triples',b)
                b.pop('input_triples',None);b.pop('field_evidence_index',None)
            self.assertTrue(all(v==bodies[ARMS[0]] for v in bodies.values()))

if __name__=='__main__':unittest.main()
