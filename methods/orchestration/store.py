"""Persistent exact-map reduction queue and model-qualified result registry.

SQLite is the durable coordination layer. Raw tensor order remains part of the
identity; no circuit is reused through an unrecorded term permutation or GL map.
Only Q is enabled in this pilot. Other coefficient domains require explicit
verifiers and separate cache namespaces.
"""
from pathlib import Path
from fractions import Fraction as Q
import copy, hashlib, importlib.util, json, os, platform, sqlite3, subprocess, sys, time, uuid
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CORE=HERE.parent/'circuits'/'circuits.py'
CSE=HERE/'signed_cse.py'
sys.path.insert(0,str(CORE.parent))
from circuits import Circuit,direct,transpose,parse_slp,verify_tensor,write_sms,enc

def packed(x):return json.dumps(x,default=enc,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(packed(x).encode()).hexdigest()
def qmatrix(m):
    if not m or not m[0] or any(len(r)!=len(m[0]) for r in m):raise ValueError('nonempty rectangular matrix required')
    return [[Q(x) for x in row] for row in m]
def mul(a,b):
    if len(a[0])!=len(b):raise ValueError('composition shape mismatch')
    return [[sum(Q(x)*Q(y) for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schemes(id TEXT PRIMARY KEY, dimensions TEXT NOT NULL, rank INTEGER NOT NULL, domain TEXT NOT NULL, dense TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS maps(id TEXT PRIMARY KEY, domain TEXT NOT NULL, matrix TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS variants(id TEXT PRIMARY KEY, scheme_id TEXT NOT NULL REFERENCES schemes(id), coordinates TEXT NOT NULL CHECK(coordinates IN ('ordinary','alternative')), kernel_maps TEXT NOT NULL, boundary_maps TEXT NOT NULL, provenance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reducers(id TEXT PRIMARY KEY, name TEXT NOT NULL, config TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, map_id TEXT NOT NULL REFERENCES maps(id), reducer_id TEXT NOT NULL REFERENCES reducers(id), seed INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','verified','invalid','timeout','error')), lease_until REAL, owner TEXT, UNIQUE(map_id,reducer_id,seed));
CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, epoch TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id), cache_hit INTEGER NOT NULL, requested_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), status TEXT NOT NULL, elapsed REAL NOT NULL, detail TEXT NOT NULL, circuit TEXT, additions INTEGER, scalars INTEGER, finished_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS programs(id TEXT PRIMARY KEY, map_id TEXT NOT NULL REFERENCES maps(id), circuit TEXT NOT NULL, additions INTEGER NOT NULL, scalars INTEGER NOT NULL, provenance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS certificates(id TEXT PRIMARY KEY, variant_id TEXT NOT NULL REFERENCES variants(id), original_path TEXT NOT NULL, sha256 TEXT NOT NULL, provenance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS derivations(id TEXT PRIMARY KEY, child_id TEXT NOT NULL REFERENCES schemes(id), parent_id TEXT REFERENCES schemes(id), operation TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS queue_status ON jobs(status);
CREATE INDEX IF NOT EXISTS map_programs ON programs(map_id,scalars,additions);
'''

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=30);self.db.row_factory=sqlite3.Row
        self.db.executescript(SCHEMA);self.db.commit()
    def close(self):self.db.close()
    def scheme(self,dense):
        if dense.get('z2',False):raise ValueError('Q-only pilot: F2 needs a separate verifier/model namespace')
        d={'n':dense['n'],'m':dense['m'],'z2':False,**{s:qmatrix(dense[s]) for s in 'uvw'}}
        verify_tensor(d);h=digest(d)
        self.db.execute('INSERT OR IGNORE INTO schemes VALUES(?,?,?,?,?)',(h,packed(d['n']),d['m'],'Q',packed(d)));return h
    def matrix(self,m):
        m=qmatrix(m);h=digest({'domain':'Q','matrix':m})
        self.db.execute('INSERT OR IGNORE INTO maps VALUES(?,?,?)',(h,'Q',packed(m)));return h
    def program(self,map_id,circuit,provenance):
        M=json.loads(self.db.execute('SELECT matrix FROM maps WHERE id=?',(map_id,)).fetchone()[0])
        C=Circuit.from_dict(copy.deepcopy(circuit))
        if C.mod is not None:raise ValueError('Q-only circuit namespace: modular arithmetic is forbidden')
        cost=C.check(M)
        # The saved literal form must independently parse back to this exact map.
        parse_slp(C.slp(),len(M[0]),len(M)).check(M)
        c=C.as_dict();h=digest({'map':map_id,'circuit':c,'provenance':provenance})
        self.db.execute('INSERT OR IGNORE INTO programs VALUES(?,?,?,?,?,?)',(h,map_id,packed(c),cost['additions'],cost['scalar_multiplications'],packed(provenance)))
        return h
    def variant(self,dense,inner=None,outer=None,provenance=None):
        sid=self.scheme(dense);source={s:qmatrix(dense[s]) for s in 'uvw'}
        if inner is None:
            inner={'u':source['u'],'v':source['v'],'w':transpose(source['w'])};outer={};coordinates='ordinary'
        else:
            if outer is None or set(inner)!=set('uvw') or set(outer)!=set('uvw'):raise ValueError('all six alternative maps required')
            inner={s:qmatrix(inner[s]) for s in 'uvw'};outer={s:qmatrix(outer[s]) for s in 'uvw'}
            if mul(inner['u'],outer['u'])!=source['u'] or mul(inner['v'],outer['v'])!=source['v'] or mul(outer['w'],inner['w'])!=transpose(source['w']):raise ValueError('alternative boundary composition mismatch')
            # A square boundary with a left/right inverse follows from full
            # factor rank, but check nonsingularity explicitly as well.
            for s in 'uvw':
                B=outer[s];n=len(B)
                if any(len(row)!=n for row in B):raise ValueError('boundary must be square')
                A=copy.deepcopy(B)
                for c in range(n):
                    pivot=next((r for r in range(c,n) if A[r][c]),None)
                    if pivot is None:raise ValueError('singular boundary')
                    A[c],A[pivot]=A[pivot],A[c];q=A[c][c];A[c]=[x/q for x in A[c]]
                    for r in range(c+1,n):
                        q=A[r][c];A[r]=[x-q*y for x,y in zip(A[r],A[c])]
            coordinates='alternative'
        kernels={s:self.matrix(M) for s,M in inner.items()};boundaries={s:self.matrix(M) for s,M in outer.items()}
        h=digest({'scheme':sid,'coordinates':coordinates,'kernel':kernels,'boundary':boundaries})
        self.db.execute('INSERT OR IGNORE INTO variants VALUES(?,?,?,?,?,?)',(h,sid,coordinates,packed(kernels),packed(boundaries),packed(provenance or {})))
        return h,kernels,boundaries
    def import_certificate(self,path,provenance=None):
        path=Path(path).resolve();raw=path.read_bytes();c=json.loads(raw);prov={**(provenance or {}),'certificate':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
        if 'inner_forward' in c and 'kernel' in c:
            dense=c['source'];inner={s:c['inner_forward'][s] if s!='w' else transpose(c['inner_forward'][s]) for s in 'uvw'}
            v,km,bm=self.variant(dense,inner,c['outer_matrices'],prov)
            for s in 'uvw':self.program(km[s],c['kernel'][s],prov|{'part':'kernel','side':s});self.program(bm[s],c['outer'][s],prov|{'part':'boundary','side':s})
        else:
            dense=c['dense'];v,km,bm=self.variant(dense,provenance=prov)
            for s in 'uvw':
                key='w_output' if s=='w' and 'w_output' in c['circuits'] else s
                self.program(km[s],c['circuits'][key],prov|{'part':'ordinary','side':s})
        h=digest({'variant':v,'sha256':prov['sha256']})
        self.db.execute('INSERT OR IGNORE INTO certificates VALUES(?,?,?,?,?)',(h,v,str(path),prov['sha256'],packed(prov)));self.db.commit();return v
    def reducer(self,name,config):
        if name not in ('direct','signed_cse','plinopt_D','plinopt_K','plinopt_G'):raise ValueError('unsupported reducer')
        implementation=CORE if name=='direct' else CSE
        config={**config,'implementation_sha256':hashlib.sha256(implementation.read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'python':platform.python_version(),'coefficient_model':'Q; additions and nonunit scales counted separately','threads':1}
        if name.startswith('plinopt_'):
            binary=Path(config['binary']).expanduser().resolve();config['binary']=str(binary);config['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
        h=digest({'name':name,'config':config});self.db.execute('INSERT OR IGNORE INTO reducers VALUES(?,?,?)',(h,name,packed(config)));self.db.commit()
        snapshot=self.path.parent/'reducers'/h;snapshot.mkdir(parents=True,exist_ok=True)
        for filename,source in [('adapter.py',Path(__file__)),('implementation.py',implementation)]:
            dst=snapshot/filename
            if not dst.exists():dst.write_bytes(source.read_bytes())
        return h
    def request(self,map_id,reducer_id,seed,epoch):
        if type(seed) is not int:raise ValueError('integer seed required')
        h=digest([map_id,reducer_id,seed]);existing=self.db.execute('SELECT status FROM jobs WHERE id=?',(h,)).fetchone()
        self.db.execute('INSERT OR IGNORE INTO jobs(id,map_id,reducer_id,seed,status) VALUES(?,?,?,?,?)',(h,map_id,reducer_id,seed,'queued'))
        self.db.execute('INSERT INTO requests(epoch,job_id,cache_hit,requested_at) VALUES(?,?,?,?)',(epoch,h,int(existing is not None and existing['status']=='verified'),time.time()));self.db.commit();return h
    def request_all(self,reducers,seed,epoch):
        count=0
        for row in self.db.execute('SELECT id FROM maps ORDER BY id').fetchall():
            for reducer in reducers:self.request(row['id'],reducer,seed,epoch);count+=1
        return count
    def claim(self,owner,lease_seconds=30):
        self.db.execute('BEGIN IMMEDIATE')
        row=self.db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
        if row:self.db.execute("UPDATE jobs SET status='running',owner=?,lease_until=? WHERE id=?",(owner,time.time()+lease_seconds,row['id']))
        self.db.commit();return None if row is None else {**dict(row),'owner':owner}
    def recover_expired(self):
        n=self.db.execute("UPDATE jobs SET status='queued',owner=NULL,lease_until=NULL WHERE status='running' AND lease_until<?",(time.time(),)).rowcount;self.db.commit();return n
    def finish(self,job,status,elapsed,detail,circuit=None):
        if status not in ('verified','invalid','timeout','error'):raise ValueError('bad terminal status')
        self.db.execute('BEGIN IMMEDIATE')
        owner=self.db.execute('SELECT owner,status FROM jobs WHERE id=?',(job['id'],)).fetchone()
        if owner['status']!='running' or owner['owner']!=job['owner']:
            self.db.rollback();raise ValueError('job lease was replaced or completed')
        cost=None
        if status=='verified':
            try:
                pid=self.program(job['map_id'],circuit,{'job_id':job['id'],'reducer_id':job['reducer_id'],'seed':job['seed']})
                cost=self.db.execute('SELECT additions,scalars FROM programs WHERE id=?',(pid,)).fetchone()
            except Exception:
                self.db.rollback();raise
        self.db.execute('INSERT INTO attempts(job_id,status,elapsed,detail,circuit,additions,scalars,finished_at) VALUES(?,?,?,?,?,?,?,?)',(job['id'],status,elapsed,packed(detail),packed(circuit) if circuit else None,None if cost is None else cost['additions'],None if cost is None else cost['scalars'],time.time()))
        self.db.execute('UPDATE jobs SET status=?,owner=NULL,lease_until=NULL WHERE id=?',(status,job['id']));self.db.commit()
    def run(self,max_jobs=100,max_seconds=30):
        self.recover_expired()
        start=time.monotonic();done=0;owner=f'local:{os.getpid()}:{uuid.uuid4()}';module=None
        while done<max_jobs and time.monotonic()-start<max_seconds:
            pending=self.db.execute("SELECT r.name,r.config FROM jobs j JOIN reducers r ON r.id=j.reducer_id WHERE j.status='queued' ORDER BY j.rowid LIMIT 1").fetchone()
            if pending and pending['name'].startswith('plinopt_') and max_seconds-(time.monotonic()-start)<json.loads(pending['config']).get('call_timeout_seconds',3):break
            job=self.claim(owner,lease_seconds=max(30,max_seconds+5))
            if job is None:break
            M=json.loads(self.db.execute('SELECT matrix FROM maps WHERE id=?',(job['map_id'],)).fetchone()[0]);r=self.db.execute('SELECT * FROM reducers WHERE id=?',(job['reducer_id'],)).fetchone();config=json.loads(r['config']);t0=time.monotonic();status='verified';c=None;detail={}
            try:
                implementation=CORE if r['name']=='direct' else CSE
                for path,key in [(implementation,'implementation_sha256'),(Path(__file__),'adapter_sha256')]+([(Path(config['binary']),'binary_sha256')] if 'binary' in config else []):
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=config[key]:raise ValueError('implementation changed after reducer registration; register a new reducer ID')
                if r['name']=='direct':c=direct(M)
                elif r['name']=='signed_cse':
                    if not all(Q(x) in (-1,0,1) for row in M for x in row):raise ValueError('signed CSE adapter requires ternary coefficients')
                    if module is None:module=load_module('queue_cse',CSE)
                    c=module.cse(M)
                else:
                    out=self.path.parent/'jobs'/job['id']/str(uuid.uuid4());out.mkdir(parents=True,exist_ok=True);write_sms(out/'target.sms',M)
                    cmd=[config['binary'],'-'+r['name'][-1],'-O',str(config.get('loops',100)),str(out/'target.sms')]
                    result=subprocess.run(cmd,text=True,capture_output=True,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PLINOPT_SEED':str(job['seed'])},timeout=config.get('call_timeout_seconds',3))
                    (out/'output.slp').write_text(result.stdout);(out/'stderr.log').write_text(result.stderr);detail={'command':cmd,'returncode':result.returncode,'directory':str(out.resolve())}
                    if result.returncode:raise RuntimeError('optimizer returned nonzero')
                    c=parse_slp(result.stdout,len(M[0]),len(M))
                c.check(M)
            except subprocess.TimeoutExpired as e:status='timeout';detail={'reason':'per-call time limit','timeout':e.timeout}
            except Exception as e:status='invalid' if isinstance(e,ValueError) else 'error';detail={'reason':repr(e)}
            self.finish(job,status,time.monotonic()-t0,detail,None if c is None else c.as_dict());done+=1
        return {'finished_jobs':done,'wall_seconds':time.monotonic()-start,'queued':self.db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]}
    def export(self):
        variants=[]
        for v in self.db.execute('SELECT * FROM variants ORDER BY id').fetchall():
            s=self.db.execute('SELECT * FROM schemes WHERE id=?',(v['scheme_id'],)).fetchone();parts={};missing=[]
            for kind,column in [('kernel','kernel_maps'),('boundary','boundary_maps')]:
                parts[kind]={}
                for side,map_id in json.loads(v[column]).items():
                    row=self.db.execute('SELECT * FROM programs WHERE map_id=? AND scalars=0 ORDER BY additions,id LIMIT 1',(map_id,)).fetchone()
                    if row is None:missing.append([kind,side]);continue
                    parts[kind][side]={'program_id':row['id'],'map_id':map_id,'additions':row['additions'],'scalars':row['scalars'],'provenance':json.loads(row['provenance'])}
            if missing:continue
            kernel=sum(x['additions'] for x in parts['kernel'].values());boundary=sum(x['additions'] for x in parts['boundary'].values())
            variants.append({'variant_id':v['id'],'scheme_id':s['id'],'dimensions':json.loads(s['dimensions']),'rank':s['rank'],'domain':s['domain'],'coordinates':v['coordinates'],'kernel_additions':kernel,'boundary_additions':boundary,'full_additions':kernel+boundary,'nonunit_scalars':0,'parts':parts,'provenance':json.loads(v['provenance']),'comparison_scope':'best retained verified signed-binary portfolio; fixed dimensions, rank, domain and coordinate metric'})
        stats=[]
        for r in self.db.execute('SELECT * FROM reducers ORDER BY name,id').fetchall():
            a=self.db.execute('SELECT a.* FROM attempts a JOIN jobs j ON j.id=a.job_id WHERE j.reducer_id=?',(r['id'],)).fetchall()
            hits=self.db.execute('SELECT COUNT(*) FROM requests q JOIN jobs j ON j.id=q.job_id WHERE j.reducer_id=? AND q.cache_hit=1',(r['id'],)).fetchone()[0]
            stats.append({'id':r['id'],'name':r['name'],'attempts':len(a),'verified':sum(x['status']=='verified' for x in a),'timeouts':sum(x['status']=='timeout' for x in a),'invalid_or_error':sum(x['status']in('invalid','error') for x in a),'wall_seconds':sum(x['elapsed'] for x in a),'cache_hits':hits,'config':json.loads(r['config'])})
        evaluations=[]
        # A whole-scheme reducer result requires all of its maps at the SAME seed.
        # Imported programs and cross-reducer portfolios remain distinct records.
        reducer_seeds=self.db.execute('SELECT DISTINCT reducer_id,seed FROM jobs ORDER BY reducer_id,seed').fetchall()
        for v in self.db.execute('SELECT * FROM variants ORDER BY id').fetchall():
            for rs in reducer_seeds:
                parts={};states=[]
                for kind,column in [('kernel','kernel_maps'),('boundary','boundary_maps')]:
                    parts[kind]={}
                    for side,map_id in json.loads(v[column]).items():
                        j=self.db.execute('SELECT * FROM jobs WHERE map_id=? AND reducer_id=? AND seed=?',(map_id,rs['reducer_id'],rs['seed'])).fetchone()
                        states.append('unrequested' if j is None else j['status'])
                        if j is not None and j['status']=='verified':
                            a=self.db.execute("SELECT additions,scalars FROM attempts WHERE job_id=? AND status='verified' ORDER BY id DESC LIMIT 1",(j['id'],)).fetchone()
                            parts[kind][side]={'job_id':j['id'],'additions':a['additions'],'scalars':a['scalars']}
                complete=all(s=='verified' for s in states)
                row={'variant_id':v['id'],'reducer_id':rs['reducer_id'],'seed':rs['seed'],'coordinates':v['coordinates'],'status':'verified' if complete else 'incomplete','map_states':states,'parts':parts}
                if complete:
                    for kind in ['kernel','boundary']:
                        row[kind]={'additions':sum(p['additions'] for p in parts[kind].values()),'scalars':sum(p['scalars'] for p in parts[kind].values())}
                    row['full']={k:row['kernel'][k]+row['boundary'][k] for k in ['additions','scalars']}
                evaluations.append(row)
        needed_programs={p['program_id'] for v in variants for part in v['parts'].values() for p in part.values()}
        programs=[]
        for h in sorted(needed_programs):
            p=dict(self.db.execute('SELECT * FROM programs WHERE id=?',(h,)).fetchone());p['circuit']=json.loads(p['circuit']);p['provenance']=json.loads(p['provenance']);p['slp']=Circuit.from_dict(copy.deepcopy(p['circuit'])).slp();programs.append(p)
        maps=[{'id':r['id'],'domain':r['domain'],'matrix':json.loads(r['matrix'])} for r in self.db.execute('SELECT * FROM maps ORDER BY id')]
        schemes=[{'id':r['id'],'dense':json.loads(r['dense'])} for r in self.db.execute('SELECT * FROM schemes ORDER BY id')]
        return {'schema_version':1,'generated_at':time.time(),'variants':variants,'evaluations':evaluations,'reducers':stats,'programs':programs,'maps':maps,'schemes':schemes,'counts':{table:self.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ['schemes','maps','variants','jobs','attempts','requests','programs','certificates','derivations']},'limitations':['Q signed-binary pilot only; no F2 namespace yet','Best-of-factor portfolio is not credited as a single reducer result','No inferred GL-equivalence reuse','Cache hits are requests, not additional independent trials','No statistical method ranking from an adaptively selected mixed corpus']}
