"""Synthetic review contracts; no synthetic label enters empirical results."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import httpx
from exps.paper2_rule_feasibility_20261004.test_pipeline import fixture
from exps.paper2_rule_verification_20261008.review import *
from exps.paper2_rule_verification_20261008.common import digest,append_event,read_events
from exps.paper2_rule_verification_20261008.runner import transport,collect_with,recover,states
from exps.paper2_rule_feasibility_20261004.analyze import replay

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.records,self.banks,doc=fixture();doc['title']='Synthetic'
        self.docs={'a':doc,'b':dict(deepcopy(doc),case_id='b')};self.rels={'P1':'member','P2':'other'}
        quote='joined Acme'
        self.rule=dict(family='source',verdict='contradicted',record_id='r',evidence=[dict(sentence_id=0,start=6,end=17,quote_sha256=sha256(quote.encode()).hexdigest())])
        self.packet=self.banks['deletion'][0];self.packet['rules']=[self.rule]
        self.check=dict(record_id='r',verdict='reject',rationale='The text says joined, not did not join.',evidence=[dict(document_id='a',sentence_id=0,quote=quote)])
        self.output=dict(decisions=[dict(ordinal=0,checks=[self.check])])
    def parse(self):return parse_review(json.dumps(self.output),self.packet,self.docs,self.records)
    def projected(self,verdict='approve',mode='automatic'):
        key=(self.packet['packet_id'],0)
        reviews={key:dict(binding=binding(self.packet,self.rule,self.docs['a'],self.records,self.rels,self.docs),verdict=verdict)}
        return project(self.banks,self.docs,self.records,self.rels,reviews,{},mode)
    def test_synthetic_comention_rejection_blocks_deletion(self):
        rows=self.parse();self.assertEqual(overall(rows[0]['checks']),'reject')
        bank,_=self.projected('reject');self.assertEqual(replay(self.records,bank,'acquire_then_repair',1)['removed_ids'],[])
    def test_absence_uncertain_does_not_authorize(self):
        self.check.update(verdict='uncertain',rationale='Unmentioned is not contradicted.',evidence=[])
        self.assertEqual(overall(self.parse()[0]['checks']),'uncertain')
        self.assertFalse(self.projected('uncertain')[1][0]['admitted'])
    def test_positive_synthetic_approval_changes_execution_only_after_acquisition(self):
        bank,rows=self.projected();self.assertTrue(rows[0]['admitted']);self.assertFalse(rows[0]['independently_validated'])
        self.assertEqual(replay(self.records,bank,'stop',1)['removed_ids'],[])
        self.assertEqual(replay(self.records,bank,'deletion_only',1)['removed_ids'],['r'])
    def test_approve_needs_exact_evidence(self):
        self.check.update(verdict='approve',evidence=[])
        with self.assertRaises(ValueError):self.parse()
    def test_wrong_quote_fails(self):
        self.check['evidence'][0]['quote']='did not join'
        with self.assertRaises(ValueError):self.parse()
    def test_wrong_document_fails(self):
        self.check['evidence'][0]['document_id']='b'
        with self.assertRaises(ValueError):self.parse()
    def test_boolean_offset_fails(self):
        self.check['evidence'][0]['sentence_id']=False
        with self.assertRaises(ValueError):self.parse()
    def test_missing_extra_or_duplicate_candidate_fails(self):
        for rows in ([],self.output['decisions']*2):
            with self.subTest(rows=rows),self.assertRaises(ValueError):parse_review(json.dumps({'decisions':rows}),self.packet,self.docs,self.records)
    def test_duplicate_json_key_fails(self):
        with self.assertRaises(ValueError):parse_review('{"decisions":[],"decisions":[]}',self.packet,self.docs,self.records)
    def test_extra_trust_field_fails(self):
        self.output['validated']=True
        with self.assertRaises(ValueError):self.parse()
    def test_type_must_check_partner_matches(self):
        self.packet['rules']=[dict(family='type',kind='forbidden',pattern=['PER','P1','ORG'])]
        with self.assertRaises(ValueError):self.parse()
        self.output['decisions'][0]['checks'].append(dict(self.check,record_id='s',evidence=[dict(document_id='b',sentence_id=0,quote='joined Acme')]))
        self.assertEqual(len(self.parse()[0]['checks']),2)
    def test_no_match_abstains(self):self.assertEqual(overall([]),'uncertain')
    def test_mixed_review_never_approves(self):
        self.assertEqual(overall([{'verdict':'approve'},{'verdict':'uncertain'}]),'uncertain')
        self.assertEqual(overall([{'verdict':'approve'},{'verdict':'reject'}]),'reject')
    def test_combination_reject_vetoes(self):
        self.assertEqual(combine('approve','reject'),'reject');self.assertEqual(combine('reject','approve'),'reject')
        self.assertEqual(combine('approve','uncertain'),'approve');self.assertEqual(combine('uncertain','approve'),'approve')
    def test_stale_binding_fails(self):
        rev={(self.packet['packet_id'],0):dict(binding=binding(self.packet,self.rule,self.docs['a'],self.records,self.rels,self.docs),verdict='approve')}
        self.docs['b']['sents'].append(['Changed'])
        with self.assertRaises(ValueError):project(self.banks,self.docs,self.records,self.rels,rev,{},'automatic')
    def test_independent_mode_never_accepts_automatic(self):self.assertFalse(self.projected(mode='independent_empty')[1][0]['admitted'])
    def test_unverified_support_quarantined(self):
        self.rule['verdict']='supported';self.assertFalse(self.projected(verdict='uncertain')[1][0]['admitted'])
    def test_public_field_allowlist(self):
        self.records[0]['injected']=True
        with self.assertRaises(ValueError):make_task(self.packet,self.docs,self.records,self.rels)
    def test_request_model_and_scope(self):
        task=make_task(self.packet,self.docs,self.records,self.rels)
        self.assertEqual(task['request']['model'],MODEL)
        payload=json.loads(task['request']['messages'][1]['content'])
        self.assertEqual(len(payload['documents']),2);self.assertNotIn('scorer',payload)
    def test_forbidden_model_never_dispatched(self):
        with self.assertRaises(ValueError):transport({'model':'gpt-forbidden'},('secret','http://unused'),None)
    def test_http_client_mock_model_mismatch(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'model':'unexpected'}))) as c:
            r=transport({'model':MODEL},('not-real','http://unit.invalid'),c)
        self.assertEqual(r['status'],'model_mismatch');self.assertFalse(r['retryable'])
    def test_durable_outage_latch_caps_calls(self):
        tasks=[dict(task_id=str(i),request={'model':MODEL}) for i in range(38)];calls=[]
        def send(p):
            calls.append(p);return dict(status='transport_error',retryable=True,raw_response='',usage=None,returned_model=None,finish_reason=None,latency_seconds=0)
        with tempfile.TemporaryDirectory() as d:
            journal=Path(d)/'journal.jsonl'
            with self.assertRaises(RuntimeError):collect_with(tasks,journal,send,sleep=lambda _:None)
            self.assertEqual(len(calls),4)
            with self.assertRaises(RuntimeError):collect_with(tasks,journal,send,sleep=lambda _:None)
            self.assertEqual(len(calls),4)
    def test_unknown_delivery_not_resent(self):
        task=dict(task_id='t',request={'model':MODEL})
        with tempfile.TemporaryDirectory() as d:
            journal=Path(d)/'journal.jsonl'
            append_event(journal,dict(kind='attempt_started',task_id='t',attempt=1,request_sha256=digest(task['request']),started_utc='synthetic'))
            rows=recover(journal,[task]);self.assertEqual(rows['t']['outcome']['uncertain_dispatches'],1)
            calls=[];collect_with([task],journal,lambda p:calls.append(p),sleep=lambda _:None);self.assertEqual(calls,[])
    def test_all_completed_tasks_not_repeated(self):
        tasks=[dict(task_id=str(i),request={'model':MODEL}) for i in range(38)]
        def send(p):return dict(status='ok',retryable=False,raw_response='{}',usage={},returned_model=MODEL,finish_reason='stop',latency_seconds=0)
        with tempfile.TemporaryDirectory() as d:
            journal=Path(d)/'journal.jsonl';rows=collect_with(tasks,journal,send,sleep=lambda _:None)
            self.assertEqual(len(rows),38)
            calls=[];collect_with(tasks,journal,lambda p:calls.append(p),sleep=lambda _:None);self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
