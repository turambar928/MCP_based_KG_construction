import unittest
from copy import deepcopy
from exps.paper2_docred.environment import GeneratedRuleEnvironment, masked_bootstrap


def fixture():
    records = [dict(record_id='a', subject_type='PER', relation='born', object_type='ORG'),
               dict(record_id='b', subject_type='PER', relation='born', object_type='LOC')]
    packets = {s: [dict(packet_id=s+str(i), source_document_id='doc'+str(i), strategy=s,
                       parse_success=True, rules=[], provenance={}, rejections=[])
                   for i in range(2)] for s in ('deletion', 'augmentation')}
    return records, packets


class EnvironmentContracts(unittest.TestCase):
    def env(self, forbidden=True, allowed=False):
        r,p = fixture()
        # Put same rule in both packets: ordering cannot affect the fixture.
        for s,enabled,kind in [('deletion',forbidden,'forbidden'),('augmentation',allowed,'allowed')]:
            for packet in p[s]:
                if enabled: packet['rules']=[dict(kind=kind,pattern=['PER','born','ORG'])]
        return GeneratedRuleEnvironment(r,p)

    def test_failed_response_consumes_budget(self):
        r,p=fixture()
        for packet in p['deletion']: packet['parse_success']=False
        e=GeneratedRuleEnvironment(r,p)
        _,reward,_,event=e.step('acquire_deletion')
        self.assertEqual(event['acquired_responses'],1)
        self.assertAlmostEqual(reward,-.004)
        self.assertEqual(e.observe()['features']['remaining_budget_fraction'],.75)

    def test_dedup_retains_origins(self):
        e=self.env();e.step('acquire_deletion');e.step('acquire_deletion')
        self.assertEqual(len(e.active),1)
        self.assertEqual(len(next(iter(e.active.values()))),2)

    def test_conflict_abstains(self):
        e=self.env(allowed=True);e.step('acquire_deletion');e.step('acquire_augmentation')
        self.assertFalse(e.mask()[2]);self.assertTrue(e.scan()['a']['conflict'])

    def test_late_permission_identity_once(self):
        e=self.env(allowed=True);e.step('acquire_deletion');e.step('repair')
        event=e.step('acquire_augmentation')[3]
        self.assertEqual(event['late_permission_ids'],['a'])
        self.assertEqual([r['record_id'] for r in e.records],['b'])
        self.assertEqual(e.step('acquire_augmentation')[3]['late_permission_ids'],[])

    def test_budget_and_terminal(self):
        e=self.env(False)
        for action in ['acquire_deletion']*2+['acquire_augmentation']*2:e.step(action)
        self.assertEqual(e.mask(),[False,False,False,True])
        with self.assertRaises(ValueError): e.step('acquire_deletion')
        self.assertEqual(e.step('stop')[1],0.)
        self.assertEqual(e.mask(),[False]*4)
        with self.assertRaises(ValueError):e.step('stop')

    def test_protect_emptying_and_no_flags(self):
        self.assertFalse(self.env().mask()[2])
        r,p=fixture();r=r[:1]
        for q in p['deletion']:q['rules']=[dict(kind='forbidden',pattern=['PER','born','ORG'])]
        e=GeneratedRuleEnvironment(r,p);e.step('acquire_deletion')
        self.assertFalse(e.mask()[2])

    def test_labels_rejected_and_unseen_packets_not_observed(self):
        r,p=fixture();r[0]['reference_triples']=[]
        with self.assertRaises(ValueError):GeneratedRuleEnvironment(r,p)
        self.assertEqual(self.env().observe(),self.env(False,True).observe())

    def test_new_violation_identity_and_reward(self):
        e=self.env();_,reward,_,event=e.step('acquire_deletion')
        self.assertEqual(event['acquisition_revealed_ids'],['a'])
        self.assertAlmostEqual(reward,-.504)
        self.assertEqual(e.step('acquire_deletion')[3]['acquisition_revealed_ids'],[])
        _,reward,_,event=e.step('repair')
        self.assertAlmostEqual(reward,.24998)
        self.assertEqual(event['edit_created_ids'],[])

    def test_terminal_has_no_bootstrap(self):
        self.assertEqual(masked_bootstrap([100]*4,[True]*4,True),0.)
        self.assertEqual(masked_bootstrap([100,2,3,4],[False,True,False,False],False),2)

    def test_same_document_queues_required(self):
        r,p=fixture();p['augmentation'][0]['source_document_id']='foreign'
        with self.assertRaises(ValueError):GeneratedRuleEnvironment(r,p)

    def test_reset_is_complete(self):
        e=self.env();before=deepcopy(e.observe());e.step('acquire_deletion');e.step('repair')
        self.assertEqual(e.reset(),before);self.assertEqual(e.events,[])


if __name__=='__main__':unittest.main()
