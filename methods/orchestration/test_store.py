"""Meaningful queue/certificate safety controls, independent of search success."""
from store import *
import tempfile,unittest

class Controls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)/'registry.sqlite';self.s=Store(self.p)
    def tearDown(self):self.s.close();self.temp.cleanup()
    def test_cache_survives_restart_and_seed_changes(self):
        m=self.s.matrix([[1,1]]);r=self.s.reducer('direct',{})
        self.s.request(m,r,7,'first');self.s.run(1,2);self.s.close();self.s=Store(self.p)
        self.s.request(m,r,7,'again');self.assertEqual(self.s.run(1,2)['finished_jobs'],0)
        self.assertEqual(self.s.db.execute('SELECT SUM(cache_hit) FROM requests').fetchone()[0],1)
        self.s.request(m,r,8,'new_seed');self.assertEqual(self.s.run(1,2)['finished_jobs'],1)
    def test_two_connections_cannot_claim_same_job(self):
        m=self.s.matrix([[1,1]]);r=self.s.reducer('direct',{});self.s.request(m,r,3,'first')
        a=self.s.claim('worker-a');b=Store(self.p)
        try:self.assertIsNone(b.claim('worker-b'))
        finally:b.close()
        self.s.db.execute('UPDATE jobs SET lease_until=0');self.s.db.commit();self.s.recover_expired();self.s.claim('worker-new')
        with self.assertRaisesRegex(ValueError,'lease'):self.s.finish(a,'verified',0,{},direct([[1,1]]).as_dict())
    def test_false_circuit_and_wrong_boundary_rejected(self):
        m=self.s.matrix([[1,1]])
        with self.assertRaises(ValueError):self.s.program(m,direct([[1,-1]]).as_dict(),{})
        d={'n':[1,1,1],'m':1,'z2':False,'u':[[1]],'v':[[1]],'w':[[1]]}
        with self.assertRaisesRegex(ValueError,'boundary'):self.s.variant(d,{s:[[1]] for s in 'uvw'},{s:[[2]] for s in 'uvw'})
        self.s.db.rollback()
    def test_nonunit_program_never_promoted_to_signed_board(self):
        d={'n':[1,1,1],'m':1,'z2':False,'u':[[1]],'v':[[1]],'w':[[1]]}
        _,maps,_=self.s.variant(d)
        C=Circuit(1);C.outputs=[C.scale(C.scale(0,2),Q(1,2))]
        for m in maps.values():self.s.program(m,C.as_dict(),{})
        self.s.db.commit();self.assertEqual(self.s.export()['variants'],[])
    def test_coefficient_domain_not_silently_coerced(self):
        with self.assertRaisesRegex(ValueError,'Q-only'):self.s.scheme({'z2':True})
        m=self.s.matrix([[2]]);c=direct([[2]]).as_dict();c['modulus']=2
        with self.assertRaisesRegex(ValueError,'Q-only'):self.s.program(m,c,{})
    def test_stale_reducer_and_short_budget(self):
        m=self.s.matrix([[1,1]]);r=self.s.reducer('direct',{})
        cfg=json.loads(self.s.db.execute('SELECT config FROM reducers WHERE id=?',(r,)).fetchone()[0]);cfg['implementation_sha256']='bad'
        self.s.db.execute('UPDATE reducers SET config=? WHERE id=?',(packed(cfg),r));self.s.db.commit()
        self.s.request(m,r,4,'stale');self.s.run(1,2)
        self.assertEqual(self.s.db.execute('SELECT status FROM jobs').fetchone()[0],'invalid')
        r=self.s.reducer('signed_cse',{});self.s.request(m,r,4,'short')
        self.assertEqual(self.s.run(1,0)['finished_jobs'],0)
        self.assertEqual(self.s.db.execute('SELECT status FROM jobs WHERE reducer_id=?',(r,)).fetchone()[0],'queued')

if __name__=='__main__':unittest.main()
