"""Independent exact linear-SLP parser, replay, transposition and cost accounting.

No optimizer-reported cost or randomized matrix-multiplication test is trusted.
Copies/sign changes are free; nontrivial constant scales are counted separately.
"""
from __future__ import annotations
import ast
import hashlib
import json
import re
from fractions import Fraction as Q
from pathlib import Path

def require(condition, message="validation failed"):
    if not condition:
        raise ValueError(message)


def enc(x):
    if isinstance(x, Q):
        return int(x) if x.denominator == 1 else str(x)
    raise TypeError(type(x))

def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, default=enc, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)

def digest(data):
    return hashlib.sha256(json.dumps(data, default=enc, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def transpose(matrix):
    return [list(row) for row in zip(*matrix)]

def canonical_data(scheme):
    require(isinstance(scheme, dict), 'scheme must be a mapping')
    require(isinstance(scheme.get('n'), (list, tuple)) and len(scheme['n']) == 3, 'three dimensions required')
    require(all(type(d) is int and d > 0 for d in scheme['n']), 'dimensions must be positive integers')
    require(type(scheme.get('m')) is int and scheme['m'] > 0, 'rank must be a positive integer')
    require(type(scheme.get('z2', False)) is bool, 'z2 must be Boolean')
    for name in ('u', 'v', 'w'):
        require(isinstance(scheme.get(name), (list, tuple)), 'factor matrix required')
        require(all(isinstance(row, (list, tuple)) for row in scheme[name]), 'factor rows required')
    return {'n': list(scheme['n']), 'm': int(scheme['m']), 'z2': bool(scheme.get('z2', False)), **{s: [[Q(x) for x in row] for row in scheme[s]] for s in ('u', 'v', 'w')}}

def verify_tensor(scheme):
    d = canonical_data(scheme)
    n, m, k = d['n']
    r = d['m']
    mod = 2 if d['z2'] else None
    widths = [n * m, m * k, k * n]
    if mod:
        for name in ('u', 'v', 'w'):
            for row in d[name]:
                require(all(x.denominator % 2 for x in row), 'F2 coefficients require odd denominators')
            d[name] = [[Q(x.numerator * pow(x.denominator, -1, 2) % 2) for x in row] for row in d[name]]
    for s, width in zip(('u', 'v', 'w'), widths):
        require(len(d[s]) == r and all((len(row) == width for row in d[s])), s)
        require(all((any(row) for row in d[s])), 'zero rank term')
    coeff = {}
    for t in range(r):
        rows = [[(j, x) for j, x in enumerate(d[s][t]) if x] for s in ('u', 'v', 'w')]
        for a, x in rows[0]:
            for b, y in rows[1]:
                for c, z in rows[2]:
                    key = (a, b, c)
                    coeff[key] = coeff.get(key, 0) + x * y * z
    checked = 0
    for a in range(n * m):
        ai, aj = divmod(a, m)
        for b in range(m * k):
            bj, bk = divmod(b, k)
            for c in range(k * n):
                ck, ci = divmod(c, n)
                x = coeff.get((a, b, c), 0)
                if mod:
                    require(Q(x).denominator == 1, 'validation failed')
                    x = int(x) % mod
                expected = int(ai == ci and aj == bj and (bk == ck))
                require(x == expected, ('Brent', a, b, c, x, expected))
                checked += 1
    return {'exact': True, 'field': 'F2' if mod else 'Q', 'identities': checked}

class Circuit:

    def __init__(self, inputs, mod=None):
        require(type(inputs) is int and inputs >= 0, 'input count must be a nonnegative integer')
        require(mod is None or type(mod) is int and mod == 2, 'only Q and F2 circuits are supported')
        self.inputs = inputs
        self.mod = mod
        self.nodes = []
        self.outputs = []

    @staticmethod
    def _wire(a, limit):
        require(type(a) is int and 0 <= a < limit, 'wire reference is outside the available range')

    def _validate(self):
        require(type(self.inputs) is int and self.inputs >= 0, 'invalid input count')
        require(self.mod is None or type(self.mod) is int and self.mod == 2, 'invalid modulus')
        require(isinstance(self.nodes, list) and isinstance(self.outputs, list), 'nodes and outputs must be lists')
        for i, node in enumerate(self.nodes, self.inputs):
            require(isinstance(node, dict) and node.get('op') in ('add', 'scale', 'zero'), 'invalid circuit operation')
            if node['op'] in ('add', 'scale'):
                self._wire(node.get('a'), i)
            if node['op'] == 'add':
                self._wire(node.get('b'), i)
            if node['op'] == 'scale':
                scalar = Q(node['c'])
                if self.mod:
                    require(scalar.denominator % 2, 'F2 scale denominator must be odd')
                    scalar = Q(scalar.numerator * pow(scalar.denominator, -1, 2) % 2)
                node['c'] = enc(scalar)
        for output in self.outputs:
            self._wire(output, self.inputs + len(self.nodes))
        return self

    def scale(self, a, c):
        self._wire(a, self.inputs + len(self.nodes))
        c = Q(c)
        if self.mod:
            require(c.denominator % self.mod, 'validation failed')
            c = Q(int(c.numerator) * pow(int(c.denominator), -1, self.mod) % self.mod)
        if c == 1:
            return a
        if not c:
            return self.const_zero()
        self.nodes.append({'op': 'scale', 'a': a, 'c': enc(c)})
        return self.inputs + len(self.nodes) - 1

    def const_zero(self):
        self.nodes.append({'op': 'zero'})
        return self.inputs + len(self.nodes) - 1

    def add(self, a, b):
        self._wire(a, self.inputs + len(self.nodes))
        self._wire(b, self.inputs + len(self.nodes))
        self.nodes.append({'op': 'add', 'a': a, 'b': b})
        return self.inputs + len(self.nodes) - 1

    def prune(self):
        self._validate()
        live = set()
        stack = list(self.outputs)
        while stack:
            a = stack.pop()
            if a < self.inputs or a in live:
                continue
            live.add(a)
            node = self.nodes[a - self.inputs]
            stack.extend((node[k] for k in ('a', 'b') if k in node))
        mapping = {i: i for i in range(self.inputs)}
        nodes = []
        for i, node in enumerate(self.nodes, self.inputs):
            if i not in live:
                continue
            new = dict(node)
            for k in ('a', 'b'):
                if k in new:
                    require(node[k] < i, 'forward reference')
                    new[k] = mapping[new[k]]
            mapping[i] = self.inputs + len(nodes)
            nodes.append(new)
        self.outputs = [mapping[a] for a in self.outputs]
        self.nodes = nodes
        return self

    def cost(self):
        self.prune()
        adds = sum((n['op'] == 'add' for n in self.nodes))
        scales = sum((n['op'] == 'scale' and Q(n['c']) not in (-1, 0, 1) for n in self.nodes))
        return {'additions': adds, 'scalar_multiplications': scales, 'signed_binary': not scales}

    def matrix(self):
        self._validate()
        values = [[Q(i == j) for j in range(self.inputs)] for i in range(self.inputs)]
        for i, node in enumerate(self.nodes, self.inputs):
            require(all((node[k] < i for k in ('a', 'b') if k in node)), 'forward reference')
            if node['op'] == 'add':
                row = [a + b for a, b in zip(values[node['a']], values[node['b']])]
            elif node['op'] == 'scale':
                row = [Q(node['c']) * a for a in values[node['a']]]
            elif node['op'] == 'zero':
                row = [Q(0)] * self.inputs
            else:
                raise ValueError(node)
            if self.mod:
                row = [Q(int(x.numerator) * pow(int(x.denominator), -1, self.mod) % self.mod) for x in row]
            values.append(row)
        return [values[a] for a in self.outputs]

    def check(self, matrix):
        expected = [[Q(x) for x in row] for row in matrix]
        if self.mod:
            expected = [[Q(int(x.numerator) * pow(int(x.denominator), -1, self.mod) % self.mod) for x in row] for row in expected]
        require(self.matrix() == expected, 'SLP coefficient mismatch')
        return self.cost()

    def transposed(self):
        self.prune()
        result = Circuit(len(self.outputs), self.mod)
        adj = [None] * (self.inputs + len(self.nodes))

        def put(i, a):
            adj[i] = a if adj[i] is None else result.add(adj[i], a)
        for i, a in enumerate(self.outputs):
            put(a, i)
        for i in reversed(range(len(self.nodes))):
            v = adj[self.inputs + i]
            node = self.nodes[i]
            if v is None:
                continue
            if node['op'] == 'add':
                put(node['a'], v)
                put(node['b'], v)
            elif node['op'] == 'scale':
                put(node['a'], result.scale(v, node['c']))
        result.outputs = [a if a is not None else result.const_zero() for a in adj[:self.inputs]]
        result.prune().check(transpose(self.matrix()))
        return result

    def as_dict(self):
        self.prune()
        return {'inputs': self.inputs, 'modulus': self.mod, 'nodes': self.nodes, 'outputs': self.outputs, 'cost': self.cost()}

    @classmethod
    def from_dict(cls, d):
        c = cls(d['inputs'], d.get('modulus'))
        c.nodes = d['nodes']
        c.outputs = d['outputs']
        return c._validate()

    def slp(self):
        name = lambda i: f'i{i}' if i < self.inputs else f't{i - self.inputs}'
        lines = []
        for i, node in enumerate(self.nodes, self.inputs):
            if node['op'] == 'add':
                rhs = name(node['a']) + '+' + name(node['b'])
            elif node['op'] == 'scale':
                rhs = f"{name(node['a'])}*({node['c']})"
            else:
                rhs = '0'
            lines.append(f'{name(i)}:={rhs};')
        lines.extend((f'o{i}:={name(a)};' for i, a in enumerate(self.outputs)))
        return '\n'.join(lines) + '\n'

def parse_slp(text, inputs, outputs, mod=None):
    require(type(outputs) is int and outputs >= 0, 'output count must be a nonnegative integer')
    c = Circuit(inputs, mod)
    env = {f'i{i}': ('wire', i) for i in range(inputs)}

    def evaluate(node):
        if isinstance(node, ast.Name):
            require(node.id in env, ('unbound', node.id))
            return env[node.id]
        if isinstance(node, ast.Constant):
            require(type(node.value) is int, 'nonexact constant')
            return ('const', Q(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            a, x = evaluate(node.operand)
            if isinstance(node.op, ast.UAdd):
                return (a, x)
            return (a, -x) if a == 'const' else ('wire', c.scale(x, -1))
        require(isinstance(node, ast.BinOp), ('unsupported syntax', ast.dump(node)))
        ta, a = evaluate(node.left)
        tb, b = evaluate(node.right)
        if ta == tb == 'const':
            if isinstance(node.op, ast.Add):
                return ('const', a + b)
            if isinstance(node.op, ast.Sub):
                return ('const', a - b)
            if isinstance(node.op, ast.Mult):
                return ('const', a * b)
            if isinstance(node.op, ast.Div):
                return ('const', a / b)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if ta == 'const' and a == 0 and tb == 'wire':
                return ('wire', c.scale(b, -1) if isinstance(node.op, ast.Sub) else b)
            if tb == 'const' and b == 0 and ta == 'wire':
                return ('wire', a)
            require(ta == tb == 'wire', 'affine constant rejected')
            if isinstance(node.op, ast.Sub):
                b = c.scale(b, -1)
            return ('wire', c.add(a, b))
        if isinstance(node.op, ast.Mult):
            require(ta != tb, 'nonlinear product rejected')
            return ('wire', c.scale(a, b) if ta == 'wire' else c.scale(b, a))
        if isinstance(node.op, ast.Div):
            require(ta == 'wire' and tb == 'const', 'nonlinear division rejected')
            return ('wire', c.scale(a, 1 / b))
        raise ValueError(ast.dump(node))
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].strip()
        if ':=' not in line:
            continue
        lhs, rhs = map(str.strip, line.split(':=', 1))
        require(re.fullmatch('[A-Za-z][A-Za-z0-9_]*', lhs), lhs)
        require(not lhs.startswith('i'), 'input reassignment rejected')
        env[lhs] = evaluate(ast.parse(rhs, mode='eval').body)
    for i in range(outputs):
        require(f'o{i}' in env, ('missing output', i))
        typ, x = env[f'o{i}']
        require(typ == 'wire' or x == 0, 'nonzero constant output')
        c.outputs.append(x if typ == 'wire' else c.const_zero())
    return c.prune()

def direct(matrix, mod=None):
    c = Circuit(len(matrix[0]), mod)
    for row in matrix:
        terms = [c.scale(i, Q(x)) for i, x in enumerate(row) if Q(x)]
        a = terms[0] if terms else c.const_zero()
        for b in terms[1:]:
            a = c.add(a, b)
        c.outputs.append(a)
    c.check(matrix)
    return c

def from_reduced(data, side):
    n, m, k = data['n']
    inputs = {'u': n * m, 'v': m * k, 'w': data['m']}[side]
    c = Circuit(inputs, 2 if data.get('z2') else None)
    aliases = list(range(inputs))

    def expression(terms):
        out = []
        for t in terms:
            i = int(t['index'])
            require(0 <= i < len(aliases), 'validation failed')
            out.append(c.scale(aliases[i], Q(t['value'])))
        require(out, 'empty reduced expression')
        a = out[0]
        for b in out[1:]:
            a = c.add(a, b)
        return a
    for terms in data.get(side + '_fresh', []):
        aliases.append(expression(terms))
    c.outputs = [expression(terms) for terms in data[side]]
    return c.prune()

def read_sms(path):
    lines = [x.strip() for x in Path(path).read_text().splitlines() if x.strip() and (not x.startswith('#'))]
    m, n, _ = lines[0].split()
    matrix = [[Q(0)] * int(n) for _ in range(int(m))]
    for line in lines[1:]:
        i, j, val = line.split()
        i, j = (int(i), int(j))
        if i == j == 0:
            break
        require(1 <= i <= int(m) and 1 <= j <= int(n), 'validation failed')
        matrix[i - 1][j - 1] = Q(val)
    return matrix

def write_sms(path, matrix):
    lines = [f'{len(matrix)} {len(matrix[0])} R']
    lines += [f'{i} {j} {Q(x)}' for i, row in enumerate(matrix, 1) for j, x in enumerate(row, 1) if Q(x)]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(lines + ['0 0 0']) + '\n')
