"""Standalone integer replay of the source and three literal circuits."""
from pathlib import Path
import json,re,hashlib
HERE=Path(__file__).resolve().parent

def require(x,message):
    if not x:raise ValueError(message)

def sparse(expr,values):
    out=[0]*len(values[0])
    for t in expr:
        require(type(t['index'])is int and 0<=t['index']<len(values),'bad sparse index')
        require(type(t['value'])is int,'noninteger coefficient')
        for j,x in enumerate(values[t['index']]):out[j]+=t['value']*x
    return out

def matrix(C):
    n=C['inputs'];values=[[int(i==j)for j in range(n)]for i in range(n)]
    for g in C['nodes']:
        require(g['op']in ['add','sub'],'nonbinary operation')
        require(all(type(g[k])is int and 0<=g[k]<len(values)for k in ['a','b']),'noncausal wire')
        sg=1 if g['op']=='add'else-1;values.append([x+sg*y for x,y in zip(values[g['a']],values[g['b']])])
    require(all(type(i)is int and 0<=i<len(values)for i in C['outputs']),'bad output')
    return [values[i]for i in C['outputs']]

def textual(path,C):
    n=C['inputs'];env={f'i{i}':[int(i==j)for j in range(n)]for i in range(n)};outputs={};cost=0
    for line in path.read_text().splitlines():
        m=re.fullmatch(r'(t\d+):=((?:i|t)\d+)([+-])((?:i|t)\d+);',line)
        if m:
            out,a,op,b=m.groups();require(out not in env and a in env and b in env,'bad SLP wire');sg=1 if op=='+'else-1;env[out]=[x+sg*y for x,y in zip(env[a],env[b])];cost+=1;continue
        m=re.fullmatch(r'o(\d+):=((?:i|t)\d+);',line);require(m is not None,'nonliteral SLP statement');i,a=m.groups();i=int(i);require(i not in outputs and a in env,'bad SLP output');outputs[i]=env[a]
    require(set(outputs)==set(range(len(C['outputs']))),'SLP output count');require(cost==len(C['nodes']),'SLP cost mismatch');require([outputs[i]for i in range(len(outputs))]==matrix(C),'SLP matrix mismatch')

def main():
    D=json.loads((HERE/'scheme.json').read_text());S=json.loads((HERE/'source.json').read_text())
    require(hashlib.sha256((HERE/'source.json').read_bytes()).hexdigest()==D['source_sha256'],'source hash')
    require(S['n']==D['shape']==[5,5,5] and S['m']==D['rank']==93,'shape/rank');require(not D['basis_change'],'basis flag')
    M={};original={}
    for s in 'uvw':
        n=93 if s=='w'else 25;values=[[int(i==j)for j in range(n)]for i in range(n)]
        for e in S.get(s+'_fresh',[]):values.append(sparse(e,values))
        original[s]=[sparse(e,values)for e in S[s]];require(original[s]==D['source_matrices'][s],'source expansion')
        C=D['circuits'][s];require(C['inputs']==n,'input count');require(len(C['outputs'])==(25 if s=='w'else 93),'output count');M[s]=matrix(C);textual(HERE/(s+'.slp'),C)
    for t in range(93):
        signs=[]
        for s in 'uv':
            row=original[s][t];require(any(row),'zero source term');j=next(j for j,x in enumerate(row)if x);sg=M[s][t][j]//row[j];require(sg in [-1,1]and M[s][t]==[sg*x for x in row],'non-sign term change');signs.append(sg)
        require(all(M['w'][j][t]==signs[0]*signs[1]*original['w'][j][t]for j in range(25)),'decoder sign compensation')
    # Sparse accumulation followed by every possible exact tensor identity.
    coeff={}
    for t in range(93):
        for a,x in enumerate(M['u'][t]):
            if not x:continue
            for b,y in enumerate(M['v'][t]):
                if not y:continue
                for c in range(25):
                    z=M['w'][c][t]
                    if z:coeff[a,b,c]=coeff.get((a,b,c),0)+x*y*z
    for a in range(25):
        for b in range(25):
            for c in range(25):require(coeff.get((a,b,c),0)==int(a%5==b//5 and c==(b%5)*5+a//5),'tensor identity')
    split=[len(D['circuits'][s]['nodes'])for s in 'uvw'];require(sum(split)==D['additions'],'count')
    print(json.dumps({'status':'PASS','rank':93,'additions':sum(split),'split':split,'scalar_total':93+sum(split),'basis_change':False,'unary_negations':0,'nonunit_scalars':0,'tensor_identities':15625,'source_pinned_and_reexpanded':True,'textual_and_json_replay':True},indent=2))

if __name__=='__main__':main()
