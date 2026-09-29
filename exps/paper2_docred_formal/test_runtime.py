import unittest,torch
from exps.paper2_docred_formal.runtime import Network,bellman,train,rollout
from exps.paper2_docred_v2.test_contracts import fixture,rule

class Runtime(unittest.TestCase):
    def test_terminal_bootstrap_is_finite_zero(self):
        a,b=Network(),Network();states=torch.zeros(3,14);masks=torch.tensor([[False]*4,[True]*4,[False,False,False,True]])
        for double in [False,True]:
            values=bellman(a,b,states,masks,torch.tensor([True,True,False]),double=double)
            self.assertTrue(torch.isfinite(values).all());self.assertEqual(values[:2].tolist(),[0.,0.])
    def test_tiny_training_and_replay(self):
        records,packets=fixture();packets['deletion'][0]['rules']=[rule()];item=dict(records=records,packets=packets)
        model,history=train([item],7,'ddqn',episodes=100)
        self.assertEqual(len(history),100);self.assertTrue(any(h['loss'] is not None for h in history))
        out=rollout(item,'ddqn',10,model);self.assertEqual(out['actual_api_calls'],0);self.assertTrue(out['events'][-1]['terminal'])
    def test_no_checkpoint_dimension_reuse(self):
        self.assertEqual(tuple(Network()(torch.zeros(14)).shape),(4,))

if __name__=='__main__':unittest.main()
