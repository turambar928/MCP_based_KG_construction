import copy,inspect,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rule_integration.runtime import ArchiveReplay,choose


def rule(rid,kind,strategy):
    return {'rule_id':rid,'kind':kind,'pattern':['A','r','B'],
            'sources':[{'strategy':strategy,'source_line':1,'unid':'synthetic'}]}


class RuntimeTests(unittest.TestCase):
    def env(self,allow=False):
        records=[{'record_id':'x','subject_type':'A','relation':'r','object_type':'B'},
                 {'record_id':'keep','subject_type':'C','relation':'r','object_type':'B'}]
        return ArchiveReplay(records,{'deletion':[rule('f','forbidden','deletion')],
                      'augmentation':[rule('a','allowed','augmentation')] if allow else []},
                      {'deletion':1,'augmentation':int(allow)})
    def test_actual_rule_enables_removal(self):
        e=self.env();self.assertFalse(e.available_actions()['repair']);e.step('acquire_deletion')
        self.assertTrue(e.available_actions()['repair']);e.step('repair')
        self.assertEqual([r['record_id'] for r in e.records],['keep'])
    def test_unknown_types_abstain_even_if_rule_names_unknown(self):
        e=self.env();e.records[0]['subject_type']='Unknown';e.packets['deletion'][0]['pattern'][0]='Unknown'
        e.step('acquire_deletion');self.assertEqual(e.scan()[0]['status'],'missing_type');self.assertFalse(e.available_actions()['repair'])
    def test_missing_endpoint_abstains(self):
        e=self.env();e.records[0]['missing_endpoint']=True;e.step('acquire_deletion')
        self.assertFalse(e.available_actions()['repair'])
    def test_permission_alone_is_open_world(self):
        e=self.env(True);e.step('acquire_augmentation');self.assertFalse(e.available_actions()['repair'])
    def test_conflict_abstains(self):
        e=self.env(True);e.step('acquire_deletion');e.step('acquire_augmentation')
        self.assertTrue(e.scan()[0]['conflict']);self.assertFalse(e.available_actions()['repair'])
    def test_late_permission_logged_without_invented_replacement(self):
        e=self.env(True);e.step('acquire_deletion');e.step('repair');_,_,event=e.step('acquire_augmentation')
        self.assertEqual([r['record_id'] for r in event['late_permissions']],['x'])
        self.assertEqual(len(e.records),1)
    def test_repeated_acquisition_rejected_without_change(self):
        e=self.env();e.step('acquire_deletion');before=copy.deepcopy(e.active)
        with self.assertRaises(ValueError):e.step('acquire_deletion')
        self.assertEqual(e.active,before)
    def test_shared_rule_merges_lineage(self):
        e=self.env();e.packets['augmentation']=[rule('f','forbidden','augmentation')]
        e.step('acquire_deletion');e.step('acquire_augmentation')
        self.assertEqual(len(e.active),1);self.assertEqual(len(e.active['f']['sources']),2)
    def test_empty_graph_guard(self):
        e=self.env();e.records=e.records[:1];e.step('acquire_deletion')
        self.assertFalse(e.available_actions()['repair'])
        with self.assertRaises(ValueError):e.step('repair')
    def test_horizon_and_stop(self):
        e=self.env();e.horizon=1;_,done,_=e.step('acquire_deletion')
        self.assertTrue(done);self.assertFalse(any(e.available_actions().values()))
        with self.assertRaises(ValueError):e.step('stop')
        e=self.env();e.step('stop');self.assertTrue(e.done)
    def test_labels_are_not_policy_input(self):
        e=self.env();records=copy.deepcopy(e.initial)
        for r in records:r.update(expected_detection='fail',data_quality='bad')
        other=ArchiveReplay(records,e.packets,e.response_counts)
        self.assertEqual(e.observe(),other.observe());self.assertEqual(e.initial,other.initial)
        self.assertEqual(list(inspect.signature(choose).parameters),['observation','order','timing'])
    def test_replay_reconstructs_edits(self):
        e=self.env(True);initial={r['record_id']:r for r in copy.deepcopy(e.records)}
        for a in ['acquire_deletion','repair','acquire_augmentation','stop']:e.step(a)
        active=set()
        for event in e.events:
            self.assertTrue(event['before']['mask'][event['action']]);active.update(event['activated_rule_ids'])
            for r in event['removed_records']:initial.pop(r['record_id'])
        self.assertEqual(initial,{r['record_id']:r for r in e.records});self.assertEqual(active,set(e.active))
    def test_order_timing_hazard_synthetic_only(self):
        counts=[]
        for timing in ['immediate','deferred']:
            e=self.env(True)
            while not e.done:e.step(choose(e.observe(),('deletion','augmentation'),timing))
            counts.append(len(e.removed))
        self.assertEqual(counts,[1,0])

if __name__=='__main__':unittest.main()
