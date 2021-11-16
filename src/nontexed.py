import html, os

def skip_braces(s, i):
    brlevel = 0
    ch = None
    prev = None
    first = True
    while brlevel or ch or first:
        first = False
        if s[i] == ch and prev != '\\': ch = None
        elif ch != None: pass
        elif s[i] in '"'"'": ch = s[i]
        elif s[i] in '([{': brlevel += 1
        elif s[i] in '}])': brlevel -= 1
        prev = s[i]
        i += 1
    return i

def read_file(f):
    with (open(f) if isinstance(f, str) else f) as file:
        for line in file: yield line.strip()

def expand_preps(g):
    for l in g:
        ls = [l]
        idx = 0
        while idx < len(ls):
            done = True
            l = ls[idx]
            i = 0
            while True:
                i = l.find('$', i)
                if i < 0 or i == len(l) - 1:
                    break
                i += 1
                if l[i] == '(':
                    i = skip_braces(l, i)
                elif l[i] == '{':
                    start = i - 1
                    end = skip_braces(l, i)
                    i = start + 2
                    prev_i = i
                    choices = ['']
                    while i < end - 1:
                        if l[i] in ('([{'):
                            i2 = skip_braces(l, i)
                            choices[-1] += l[i:i2]
                            i = i2
                        elif l[i] == ',' and l[i - 1] != '\\':
                            choices.append('')
                            prev_i = i = i + 1
                        elif l[i] == ',' and l[i - 1] == '\\':
                            choices[-1] = choices[-1][:-1] + ','
                            i += 1
                        else:
                            choices[-1] += l[i]
                            i += 1
                    ls[idx:idx+1] = [l[:start]+j+l[end:] for j in choices]
                    choices.append(l[prev_i:i])
                    done = False
                    break
            if done: idx += 1
        for i in ls: yield i

def parse_mdlike(g):
    in_ul = 0
    for l in g:
        if set(l.split(' ', 1)[0]) == {'*'}:
            cnt = l.find(' ')
            while in_ul < cnt:
                yield ('<ul>\n', None)
                in_ul += 1
            while in_ul > cnt:
                yield ('</ul>\n', None)
                in_ul -= 1
            yield ('<li>%s</li>\n', l.split(' ', 1)[-1])
        else:
            while in_ul > 0:
                yield ('</ul>\n', None)
                in_ul -= 1
            if set(l.split(' ', 1)[0]) == {'#'}:
                yield ('<h%d>%%s</h%d>\n'%((l.find(' '),)*2), l.split(' ', 1)[-1])
            else:
                yield ('<p>%s</p>', l)
    if in_ul: yield ('</ul>\n', None)

def html8capitals():
    ans = None
    first = True
    quote = False
    prev = None
    next_unescaped = False
    while True:
        ans = yield ans
        if next_unescaped: next_unescaped = False
        elif ans == '"':
            if quote: ans = '&raquo;'
            else: ans = '&laquo;'
            quote = not quote
        elif ans.isalnum() and first:
            ans = ans.upper()
            first = False
        elif ans == ' ' and prev == '.': first = True
        elif ans == '$':
            next_unescaped = True
            ans = ''
        else: ans = html.escape(ans)
        prev = ans

def parse_wiki_links(s):
    data = (s+' ').split('wiki://')
    for i in range(1, len(data)):
        a, b = data[i].split(' ', 1)
        a = '$'+'$'.join('<a href="https://ru.wikipedia.org/wiki/'+html.escape(a)+'">'+html.escape(a).replace('_', ' ').replace('$', '$$')+'</a>')
        data[i] = a+' '+b.replace('$', '$$')
    data[0] = data[0].replace('$', '$$')
    return ''.join(data)[:-1]

def parse_formulas(g):
    for t, l in g:
        if l == None:
            yield (t, l)
            continue
        elif l.startswith('[[') and l.endswith(']]'):
            yield (t, [{'type': 'selectfile', 'data': l[2:-2]}])
            continue
        elif l == '$!pagebreak':
            yield (t, [{'type': 'pagebreak', 'data': ''}])
            continue
        if '$TODO' in l:
            l = l.replace('$TODO', 'TODO')
            t %= '<font color="red">%s</font>'
        l += '$('
        ans = []
        g2 = html8capitals()
        next(g2)
        i = 0
        while True:
            i2 = l.find('$(', i)
            ans.append({'type': 'text', 'data': ''})
            for c in parse_wiki_links(l[i:i2]):
                ans[-1]['data'] += g2.send(c)
            if i2 == len(l) - 2: break
            i3 = skip_braces(l, i2+1)
            i = i3
            g2.send('formula')
            ans.append({'type': 'formula', 'data': parse_formula(l[i2+2:i3-1])})
        yield (t, ans)

import ast

def parse_formula(fm):
    fm2 = ''
    i = 0
    by_idx = {}
    while i < len(fm):
        if i in by_idx:
            fm2 += by_idx[i]
            del by_idx[i]
            i += 1
        elif fm[i] in '"'"'":
            i2 = skip_braces(fm, i)
            fm2 += fm[i:i2]
            i = i2
        else:
            if fm[i] == '$':
                if fm[i:i+6] == '$range' and fm[i+6] != '_' and not fm[i+6].isalnum():
                    assert fm[i+6] in ('(', '[')
                    i2 = skip_braces(fm, i+6)
                    assert fm[i2-1] in (')', ']')
                    by_idx[i+6] = '('
                    by_idx[i2-1] = ', tp="'+fm[i+6]+fm[i2-1]+'")'
                elif fm[i:i+3] == '$if' and fm[i+3] != '_' and not fm[i+3].isalnum():
                    assert fm[i+3] == '('
                    i2 = skip_braces(fm, i+3)
                    assert fm[i2-1] == ')'
                    by_idx[i2-1] = ') else (_)'
                elif i < len(fm) - 1 and fm[i + 1] in ('{', '['):
                    fm2 += '__dollar['
                    i2 = skip_braces(fm, i + 1)
                    fm = fm[:i2]+']'+fm[i2:]
                else:
                    fm2 += '__dollar._'
            else: fm2 += fm[i]
            i += 1
    try: return ast.parse('('+fm2+')')
    except SyntaxError: raise SyntaxError(fm2)

OPS = {'In': '&isin;', 'NotIn': '&notin;',
    'Eq': ' = ', 'NotEq': ' &ne; ', 'Gt': ' &gt; ', 'GtE': ' &ge; ', 'Lt': ' &lt; ', 'LtE': ' &le; ',
    'Add': ('%s+%s', 8, 8, 9),
    'Sub': ('%s&ndash;%s', 8, 8, 9),
    'Mult': ('%s&middot;%s', 9, 9, 10),
    'FloorDiv': ('<table style="display: inline-table; vertical-align: middle; margin-left: 1px; margin-right: 1px" cellspacing=0><tr><td align="center" style="border-bottom: 1px solid black">%s</td></tr><tr><td align="center">%s</td></tr></table>', 10, 0, 0),
    'Div': ('%s/%s', 9, 9, 10),#('<table style="display: inline-table; vertical-align: middle" cellspacing=0><tr><td><sub>%s</sub></td><td>/</td></tr><tr><td>/</td><td><sup>%s</sup></td></tr></table>', 9, 0, 0),
    'Pow': ('%s<sup>%s</sup>', 11, 12, -1),
    'And': ('&and;', 2),
    'Or': ('&or;', 1),
    'BitAnd': ('%s&cap;%s', 7, 7, 8),
    'BitSub': ('%s\\%s', 6, 6, 7),
    'BitOr': ('%s&cup;%s', 5, 5, 6),
    'BitXor': ('%s&#8710;%s', 6, 6, 7),
    'UAdd': ('+%s', 9),
    'USub': ('&ndash;%s', 9),
    'Not': ('<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px">%s</span>', 4)
}
DOLLAR = {k: '&%s;'%k for k in html.entities.name2codepoint}
DOLLAR.update({'R': '&#8477;', 'N': '&#8469;', 'Z': '&#8484;', 'C': '&#8450;', 'Q': '&#8474;', 'P': '&#8473;', 'B0': 'B&#778;'})
for i in range(0x41, 0x5b):
    DOLLAR['SCRIPT'+chr(i)] = '&#%d;'%(i+0x1d4d0)

BLOCK = '''
<table cellpadding=0 cellspacing=0 style="position: absolute; top: 0; left: 0; width: 100%; height: 100%">
<tr style="transform: translate(0, 0)"><td style="border-top: 2px solid black; border-right: 2px solid black; border-top-right-radius: 10px"></td><td></td></tr>
<tr style="transform: translate(-2px, 0)"><td></td><td style="border-bottom: 2px solid black; border-left: 2px solid black; border-bottom-left-radius: 10px"></td></tr>
<tr style="transform: translate(-2px, 0)"><td></td><td style="border-top: 2px solid black; border-left: 2px solid black; border-top-left-radius: 10px"></td></tr>
<tr style="transform: translate(0, 0)"><td style="border-bottom: 2px solid black; border-right: 2px solid black; border-bottom-right-radius: 10px"></td><td></td></tr>
</table>
'''

BLOCK_INT = '''
<table cellpadding=0 cellspacing=0 style="display: inline-table; vertical-align: middle">
<tr>
<td colspan="2"><sub>%s</sub></td>
<td></td>
</tr>
<tr>
<td></td>
<td style="transform: translate(-2px, 0); width: 3px; height: 5px; border-top: 2px solid black; border-left: 2px solid black; border-top-left-radius: 5px; border-top-right-radius: 5px"></td>
<td></td>
</tr>
<tr>
<td style="border-right: 2px solid black"></td>
<td></td>
<td>%s</td>
</tr>
<tr>
<td style="width: 3px; height: 5px; border-bottom: 2px solid black; border-right: 2px solid black; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px"></td>
<td></td>
<td></td>
</tr>
<tr>
<td colspan="2"><sup>%s</sup></td>
<td></td>
</tr>
</table>
'''

BLOCK_INTED = '''
<table cellpadding=0 cellspacing=0 style="display: inline-table; vertical-align: middle">
<tr>
<td rowspan="3" style="border-right: 1px solid black">%s</td>
<td><sup>%s</sup></td>
</tr>
<tr>
<td></td>
</tr>
<tr>
<td><sub>%s</sub></td>
</tr>
</table>
'''

class SimpleExpr(str):
    __slots__ = ()

class RightSimpleExpr(str):
    __slots__ = ()

class LeftSimpleExpr(str):
    __slots__ = ()

def format_formula(tr, rank=-1, wtf=None):
    if isinstance(tr, ast.Module):
        assert len(tr.body) == 1 and isinstance(tr.body[0], ast.Expr)
        return format_formula(tr.body[0].value)
    elif isinstance(tr, ast.BinOp):
        a = tr.left
        b = tr.op
        c = tr.right
        op, r, rl, rr = OPS[type(tr.op).__name__]
        if isinstance(tr.op, ast.BitAnd) and isinstance(c, ast.UnaryOp) and isinstance(c.op, ast.Invert):
            op, r, rl, rr = OPS['BitSub']
            c = c.operand
        left = format_formula(a, rl)
        right = format_formula(c, rr)
        good = type(left) if isinstance(tr.op, ast.Pow) else str
        if isinstance(tr.op, ast.Mult) and (isinstance(left, (LeftSimpleExpr, RightSimpleExpr, SimpleExpr)) and isinstance(right, SimpleExpr) or isinstance(left, RightSimpleExpr) and isinstance(right, RightSimpleExpr)):
            op = '%s%s'
            good = RightSimpleExpr if isinstance(left, RightSimpleExpr) else SimpleExpr
        ans = good(op % (left, right))
        if r < rank: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, ast.Compare):
        ops = tr.ops[:]
        comparators = tr.comparators[:]
        if len(ops) == 1 and isinstance(ops[0], (ast.Eq, ast.NotEq)) and isinstance(tr.left, ast.BinOp) and isinstance(tr.left.op, ast.Mod):
            if isinstance(comparators[0], ast.Num) and comparators[0].n == 0:
                ans = format_formula(tr.left.left, 4) + ('<span style="display: inline-block; position: relative; margin-left: 3px; margin-right: 3px"><span style="position: absolute; top: 0; left: -1.5px; transform: scaleX(1.5) scaleY(0.8)">/</span>&vellip;</span>' if isinstance(ops[0], ast.NotEq) else '&vellip;') + format_formula(tr.left.right, 4)
            else:
                ans = format_formula(tr.left.left, 4) + ('&#8802;' if isinstance(ops[0], ast.NotEq) else '&equiv;') + format_formula(comparators[0], 4) + ' (mod ' + format_formula(tr.left.right, 0) + ')'
        elif len(ops) == 1 and isinstance(ops[0], ast.In) and isinstance(comparators[0], ast.Call) and isinstance(comparators[0].func, ast.Attribute) and isinstance(comparators[0].func.value, ast.Name) and comparators[0].func.value.id == '__dollar' and comparators[0].func.attr == '_range_':
            left = format_formula(tr.left, 4)
            right = ','.join(format_formula(i, 0) for i in comparators[0].args)
            ans = left+'=<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px; margin-left: 0; margin-right: 0; margin-bottom: 0; padding: 0">'+right+'</span>'
        else:
            ans = format_formula(tr.left, 4)
            for i, j in zip(ops, comparators):
                op = OPS[type(i).__name__]
                if op == '=' and wtf == 'equiv': op = '&equiv;'
                elif op == '=' and wtf == 'nequiv': op = '&nequiv;'
                ans += op + format_formula(j, 4)
        if rank > 4: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, ast.Name):
        tr_id = tr.id
        while tr_id.startswith('__'): tr_id = tr_id[2:]
        if tr_id.startswith('_'):
            return '<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px; margin-left: 0; margin-right: 0; margin-bottom: 0; padding: 0"><i>'+html.escape(tr_id[1:])+'</i></span>'
        return SimpleExpr('<i>'+html.escape(tr_id)+'</i>')
    elif isinstance(tr, ast.Attribute):
        if isinstance(tr.value, ast.Name) and tr.value.id == '__dollar':
            assert tr.attr[:1] == '_'
            return SimpleExpr(DOLLAR[tr.attr[1:]])
        return format_formula(tr.value, rank) + ' ' + html.escape(tr.attr[1:] if tr.attr.startswith('_') else tr.attr)
    elif isinstance(tr, ast.SetComp):
        ans = '{&forall;'+format_formula(tr.elt)
        last_such = False
        for i in tr.generators:
            if not last_such:
                last_such = True
                ans += ' | '
            else:
                ans += ', '
            is_dollar_range = False
            if isinstance(i.iter, ast.Call) and isinstance(i.iter.func, ast.Attribute) and isinstance(i.iter.func.value, ast.Name) and i.iter.func.value.id == '__dollar' and i.iter.func.attr == '_range_':
                is_dollar_range = True
                ans += format_formula(i.target, 4)
                ans += '=<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px; margin-left: 0; margin-right: 0; margin-bottom: 0; padding: 0">'
                ans += ','.join(format_formula(i, 0) for i in i.iter.args)
                ans += '</span>'
            else:
                ans += format_formula(i.target, 4) + OPS['In'] + format_formula(i.iter, 4)
            if isinstance(i.iter, ast.Call) and isinstance(i.iter.func, ast.Name) and i.iter.func.id == 'range' or is_dollar_range:
                if not last_such:
                    last_such = True
                    ans += ' | '
                else:
                    ans += ', '
                ans += format_formula(i.target, 4) + OPS['In'] + DOLLAR['N']
            for j in i.ifs:
                if not last_such:
                    last_such = True
                    ans += ' | '
                else:
                    ans += ', '
                ans += format_formula(j, 4)
        ans += '}'
        return ans
    elif isinstance(tr, ast.GeneratorExp):
        ans = format_formula(tr.elt)
        last_such = False
        for i in tr.generators:
            if not last_such:
                last_such = True
                ans += ' | '
            else:
                ans += ', '
            ans += format_formula(i.target, 4) + OPS['In'] + format_formula(i.iter, 4)
            if isinstance(i.iter, ast.Call) and isinstance(i.iter.func, ast.Name) and i.iter.func.id == 'range':
                if not last_such:
                    last_such = True
                    ans += ' | '
                else:
                    ans += ', '
                ans += format_formula(i.target, 4) + OPS['In'] + DOLLAR['N']
            for j in i.ifs:
                if not last_such:
                    last_such = True
                    ans += ' | '
                else:
                    ans += ', '
                ans += format_formula(j, 4)
        if rank > 0: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, ast.Subscript):
        if isinstance(tr.value, ast.Name) and tr.value.id == '__dollar':
            if isinstance(tr.slice.value, (ast.List, ast.Set)):
                if isinstance(tr.slice.value, ast.Set):
                    first = '<td rowspan="'+str(len(tr.slice.value.elts))+'" style="position: relative; width: 10px; transform: scaleX(-1)">'+BLOCK+'</td>'
                    last = '<td rowspan="'+str(len(tr.slice.value.elts))+'" style="position: relative; width: 10px">'+BLOCK+'</td>'
                else:
                    first = '<td rowspan="'+str(len(tr.slice.value.elts))+'" style="border-top: 2px solid black; border-bottom: 2px solid black; border-left: 2px solid black"></td>'
                    last = ''
                ans = '<table style="display: inline-table; vertical-align: middle">'
                for i in tr.slice.value.elts:
                    ans += '<tr>'+first+'<td>'+format_formula(i)+'</td>'+last+'</tr>'
                    first = last = ''
                ans += '</table>'
                return ans
            else: assert False, tr.value
        ans = format_formula(tr.value)
        good = type(ans)
        bad = False
        if isinstance(tr.slice.value, ast.Str):
            idx = html.escape(tr.slice.value.s)
            bad = True
        else:
            idx = '<sub>'+format_formula(tr.slice.value)+'</sub>'
            if isinstance(tr.slice.value, ast.Tuple): idx = '<sub>'+idx[6:-7]+'</sub>'
        if False: #isinstance(tr.value, ast.Subscript) and not bad:
            ans = ans[:-6]+idx+'</sub>'
        else:
            ans += idx
        return good(ans)
    elif isinstance(tr, ast.Call):
        kwds = {i.arg: i.value for i in tr.keywords}
        if isinstance(tr.func, ast.Name):
            if tr.func.id == 'range':
                if 'tp' in kwds: tp = kwds['tp'].s
                else: tp = '[)'
                arg0 = format_formula(tr.args[0], 0)
                if len(tr.args) == 1:
                    arg1 = arg0
                    arg0 = '1'
                    tp = '[]'
                else:
                    arg1 = format_formula(tr.args[1], 0)
                return tp[0]+arg0+';'+arg1+tp[1]
            elif tr.func.id == 'set':
                assert not tr.args
                return '&empty;'
            elif tr.func.id in ('all', 'any'):
                ans = '&forall;'+', '.join(format_formula(i, -1 if rank < 0 else 4) for i in tr.args)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'exists':
                ans = '&exist;'+', '.join(format_formula(i, -1 if rank < 0 else 4) for i in tr.args)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'nexists':
                ans = '&#8708;'+', '.join(format_formula(i, -1 if rank < 0 else 4) for i in tr.args)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'unique':
                ans = '&exist;!'+', '.join(format_formula(i, -1 if rank < 0 else 4) for i in tr.args)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'abs':
                ans = '<span style="display: inline-block; border-left: 1px solid black; border-right: 1px solid black; padding: 2px">'+format_formula(tr.args[0], 0, 'abs')+'</span>'
                #if rank > 11: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'round':
                ans = '['+format_formula(tr.args[0], 0, 'abs')+']'
                #if rank > 11: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id == 'factorial':
                ans = format_formula(tr.args[0], 11)+'!'
                if rank > 12: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.id in ('qrt', 'sqrt'):
                if tr.func.id == 'qrt':
                    p, n = tr.args
                    p = format_formula(p, 0)
                    n = format_formula(n, 0)
                else:
                    p = ''
                    n = format_formula(tr.args[0], 0)
                return SimpleExpr(('<sup><u>'+p+'</u></sup>' if p else '')+'&radic;'+'<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px">'+n+'</span>')
            elif tr.func.id in ('dim', 'ker', '__def', 'im', 'rank', 'tr'):
                expr = format_formula(tr.args[0], 10)
                ans = '<i>'+tr.func.id.replace('__', '')+'</i>&nbsp;'+expr
                if rank > 10: ans = SimpleExpr('('+ans+')')
                return ans
        if isinstance(tr.func, ast.Attribute):
            if tr.func.attr == 'then':
                ans = format_formula(tr.func.value, 0)+' &#8658; '+format_formula(tr.args[0], 0)
                if rank > 0: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'issubset':
                ans = format_formula(tr.func.value, 4)
                is_dollar_range = False
                if isinstance(tr.func.value, ast.Tuple):
                    ans = ans[1:-1]
                    if isinstance(tr.args[0], ast.Call) and isinstance(tr.args[0].func, ast.Attribute) and isinstance(tr.args[0].func.value, ast.Name) and tr.args[0].func.value.id == '__dollar' and tr.args[0].func.attr == '_range_':
                        ans += '=<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px; margin-left: 0; margin-right: 0; margin-bottom: 0; padding: 0">'
                        ans += ','.join(format_formula(i, 0) for i in tr.args[0].args)
                        ans += '</span>'
                        is_dollar_range = True
                    ans += '&isin;'
                elif 'e' in kwds:
                    ans += '&sube;'
                else:
                    ans += '&sub;'
                if not is_dollar_range: ans += format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'issuperset':
                ans = format_formula(tr.func.value, 4)
                if 'e' in kwds:
                    ans += '&supe;'
                else:
                    ans += '&sup;'
                ans += format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'cross':
                ans = format_formula(tr.func.value, 9)+'&times;'+format_formula(tr.args[0], 9)
                if rank > 9: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'equals':
                ans = format_formula(tr.func.value, 4)+'~'+format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'nequals':
                ans = format_formula(tr.func.value, 4)+'&#8769;'+format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif isinstance(tr.func.value, ast.Name) and tr.func.value.id == '__dollar':
                if tr.func.attr == '_let':
                    ans = format_formula(tr.args[0], 0)+' &#8660; '+format_formula(tr.args[1], 0)
                    if rank > 0: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr == '_ddx':
                    ans = format_formula(tr.args[0], 14)+"'"
                    if rank > 14: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr in ('_matrix', '_table'):
#                   assert all(isinstance(i, ast.Tuple) for i in tr.args)
                    ans = '<table style="display: inline-table; vertical-align: middle"'+(' cellpadding="5px"' if tr.func.attr == '_matrix' else (' border="1"' if 'borderless' not in kwds else ''))+' cellspacing="0">'
                    lr = '<td rowspan="{cnt}" style="width: 10px; border-top: 2px solid black; border-{side}: 2px solid black; border-bottom: 2px solid black; border-top-{side}-radius: 10px; border-bottom-{side}-radius: 10px"></td>'
                    left = lr.format(cnt=len(tr.args), side='left')
                    right = lr.format(cnt=len(tr.args), side='right')
                    td = td1 = 'td align="center"' if tr.func.attr == '_matrix' else 'td'
                    if wtf in ('abs', 'block') or tr.func.attr == '_table':
                        left = right = ''
                        if tr.func.attr == '_table' and 'headless' not in kwds: td = 'th'
                    width = max(len(i.elts) if isinstance(i, ast.Tuple) else 1 for i in tr.args)
                    br = ' style="border-right: 1px solid black"' if 'block' in kwds else ''
                    bd = ' style="border-bottom: 1px solid black"' if 'block' in kwds else ''
                    br_bd = ' style="border-right: 1px solid black; border-bottom: 1px solid black"' if 'block' in kwds else ''
                    block_tag = 'block' if 'block' in kwds else None
                    for idx, i in enumerate(tr.args):
                        if idx == len(tr.args) - 1:
                            bd = ''
                            br_bd = br
                        ans += '<tr>'+left
                        if isinstance(i, ast.Tuple):
                            for j in i.elts[:-1]:
                                ans += '<'+td+br_bd+'>'+format_formula(j, wtf=block_tag)+'</'+td+'>'
                            if i.elts: ans += '<'+td+bd+'>'+format_formula(i.elts[-1], wtf=block_tag)+'</'+td+'>'
                        else:
                            ans += '<'+td+' colspan="'+str(width)+'"'+bd+'>'+format_formula(i, wtf=block_tag)+'</'+td+'>'
                        ans += right+'</tr>'
                        left = right = ''
                        td = td1
                    ans += '</table>'
                    return SimpleExpr(ans)
                elif tr.func.attr in ('_Sigma', '_Pi', '_Cap', '_Cup'):
                    if len(tr.args) == 1:
                        down = up = ''
                        expr = tr.args[0]
                    elif len(tr.args) == 2:
                        down, expr = tr.args
                        up = ''
                        down = format_formula(down, 0)
                    else:
                        down, up, expr = tr.args
                        down = format_formula(down, 0)
                        up = format_formula(up, 0)
                    expr = format_formula(expr, 9)
                    if tr.func.attr == '_Sigma':
                        sym = '&sum;'
                    elif tr.func.attr == '_Pi':
                        sym = '&prod;'
                    elif tr.func.attr == '_Cap':
                        sym = '&#8898;'
                    elif tr.func.attr == '_Cup':
                        sym = '&#8899;'
                    ans = '<table style="display: inline-table; vertical-align: middle" cellspacing=0><tr><td align="center"><sub>'+up+'</sub></td></tr><tr><td align="center" style="transform: scale(1.5)">'+sym+'</td></tr><tr><td align="center"><sup>'+down+'</sup></td></table>'+expr
                    if rank > 9: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr in ('_c', '_d', '_r'):
                    ans = ('d' if tr.func.attr=='_d' else tr.func.attr[1].upper())+format_formula(tr.args[0], 11)
                    if rank > 11: ans = SimpleExpr('('+ans+')')
                    return ans
                elif (tr.func.attr.startswith('_c') or tr.func.attr.startswith('_d')) and tr.func.attr[2:].isnumeric():
                    ans = ('d' if tr.func.attr[:2]=='_d' else tr.func.attr[1].upper())+'<sup>%s</sup>'%tr.func.attr[2:]+format_formula(tr.args[0], 11)
                    if rank > 11: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr == '_Int':
                    if len(tr.args) == 3:
                        down, up, expr = tr.args
                        down = format_formula(down, 0)
                        up = format_formula(up, 0)
                    else:
                        expr, = tr.args
                        down = up = ''
                    expr = format_formula(expr, 9)
                    return BLOCK_INT%(up, expr, down)
                elif tr.func.attr == '_Inted':
                    down, up, expr = tr.args
                    down = format_formula(down, 0)
                    up = format_formula(up, 0)
                    expr = format_formula(expr, 8)
                    ans = BLOCK_INTED%(expr, up, down)
                    if rank > 8: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr in ('_lim', '_sup', '_inf', '_max', '_min', '_upperlim', '_lowerlim'):
                    name = tr.func.attr[1:]
                    if name == 'lowerlim': name = '<u>lim</u>'
                    elif name == 'upperlim': name = '<span style="display: inline-block; border-top: 1px solid black; margin-top: 3px">lim</span>'
                    if len(tr.args) == 1:
                        down = ''
                        expr = tr.args[0]
                    else:
                        down, expr = tr.args
                        down = format_formula(down, 0)
                    expr = format_formula(expr, -1 if rank < 0 else 9)
                    if down:
                        ans = '<table style="display: inline-table; vertical-align: middle" cellspacing=0><tr><td><sub style="opacity: 0">plh</sub></td><td></td></tr><tr><td align="center">'+name+'</td><td>'+expr+'</td></tr><tr><td align="center"><sup>'+down+'</sup></td><td></td></table>'
                    else:
                        ans = name+' '+expr
                    if rank > 9: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr == '_L':
                    ans = '&lt;'+', '.join(format_formula(i, 0) for i in tr.args)+'&gt;'
                    if rank > 11: ans = SimpleExpr('('+ans+')')
                    return ans
                elif tr.func.attr == '_term':
                    return format_formula(tr.args[0], rank, 'term')
                elif tr.func.attr == '_xor':
                    ans = format_formula(tr.args[0])
                    assert ans in ('<i>'+x+'</i>' for x in list(map(chr, range(ord('A'), ord('Z')+1)))+list(map(chr, range(ord('a'), ord('z')+1))))
                    ans = ans[:-4]+'&#770;'+ans[-4:]
                    return SimpleExpr(ans)
                elif tr.func.attr == '_wave':
                    ans = format_formula(tr.args[0])
                    assert ans in ('<i>'+x+'</i>' for x in list(map(chr, range(ord('A'), ord('Z')+1)))+list(map(chr, range(ord('a'), ord('z')+1))))
                    ans = ans[:-4]+'&#771;'+ans[-4:]
                    return SimpleExpr(ans)
                elif tr.func.attr == '_always':
                    return format_formula(tr.args[0], rank, 'equiv')
                elif tr.func.attr == '_not_always':
                    return format_formula(tr.args[0], rank, 'nequiv')
                elif tr.func.attr == '_part':
                    ans = '<span style="font-size: 130%">&part;</span>'+format_formula(tr.args[0], 11)
                    if rank > 11: ans = '('+ans+')'
                    return SimpleExpr(ans)
                elif tr.func.attr.startswith('_part') and tr.func.attr[5:].isnumeric():
                    ans = '<span style="font-size: 130%">&part;</span><sup>%d</sup>'%int(tr.func.attr[5:])+format_formula(tr.args[0], 11)
                    if rank > 11: ans = '('+ans+')'
                    return SimpleExpr(ans)
                elif tr.func.attr == '_nop':
                    return str(format_formula(tr.args[0], rank))
                elif tr.func.attr == '_pre':
                    return '<span style="font-family: monospace">'+format_formula(tr.args[0]).replace('\n', '<br/>')+'</span>'
                elif tr.func.attr == '_link':
                    assert isinstance(tr.args[0], ast.Str)
                    return '<a href="'+html.escape(tr.args[0].s)+'">'+html.escape(tr.args[0].s)+'</a>'
                elif tr.func.attr == '_html' and os.environ.get('UNSAFE', '0') == '1':
                    assert isinstance(tr.args[0], ast.Str)
                    return tr.args[0].s
            elif tr.func.attr == 'if_':
                ans = format_formula(tr.func.value, 0) + ' | ' + format_formula(tr.args[0], 0)
                if rank > 0: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'perp':
                ans = format_formula(tr.func.value, 4) + '&perp;' + format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'parallel':
                ans = format_formula(tr.func.value, 4) + ' &parallel; ' + format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'asymp':
                ans = format_formula(tr.func.value, 4) + '&asymp;' + format_formula(tr.args[0], 4)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'mapsto':
                ans = format_formula(tr.func.value, 11)+'&#8614;'+format_formula(tr.args[0], 11)
                if rank > 11: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'xor':
                ans = format_formula(tr.func.value, 6)+'&oplus;'+format_formula(tr.args[0], 7)
                if rank > 6: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'plusmn':
                ans = format_formula(tr.func.value, 8)+'&plusmn;'+format_formula(tr.args[0], 9)
                if rank > 8: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'down':
                ans = format_formula(tr.func.value, 7)+'&darr;'+format_formula(tr.args[0], 8)
                if rank > 7: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'induce':
                ans = format_formula(tr.func.value, 6)+'|'+format_formula(tr.args[0], 7)
                if rank > 6: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'forall':
                ans = format_formula(tr.func.value, -1 if rank < 0 else 4)+'&forall;'+', '.join(format_formula(i, -1 if rank < 0 else 4) for i in tr.args)
                if rank > 4: ans = SimpleExpr('('+ans+')')
                return ans
            elif tr.func.attr == 'concat':
                left = format_formula(tr.func.value, rank)
                right = format_formula(tr.args[0], rank)
                if isinstance(left, (LeftSimpleExpr, RightSimpleExpr, SimpleExpr)) and isinstance(right, SimpleExpr) or isinstance(left, RightSimpleExpr) and isinstance(right, RightSimpleExpr):
                    good = RightSimpleExpr if isinstance(left, RightSimpleExpr) else SimpleExpr
                else:
                    good = str
                return good(left+right)
            elif tr.func.attr == 'sub':
                ans = format_formula(tr.func.value, 11) + '[' + format_formula(tr.args[0], 0) + ']'
                if rank > 11: ans = SimpleExpr('(' + ans + ')')
                return ans
            else:
                print('warning: unknown method', tr.func.attr)
        if isinstance(tr.func, ast.Call) and isinstance(tr.func.func, ast.Name) and tr.func.func.id in ('all', 'any', 'exists', 'unique'):
            ans = format_formula(tr.func, rank)+' '+format_formula(tr.args[0], rank)
            if rank > 0: ans = SimpleExpr('('+ans+')')
            return ans
        if len(tr.args) == 1 and isinstance(tr.args[0], ast.Dict):
            ans = format_formula(tr.func, 11)+':'+format_formula(tr.args[0], 11, wtf)
            if rank > 11: ans = SimpleExpr('('+ans+')')
            return ans
        ans = format_formula(tr.func, 11) + '(' + ', '.join(format_formula(i, 0) for i in tr.args) + ')'
        if rank > 11: ans = '('+ans+')'
        return RightSimpleExpr(ans)
    elif isinstance(tr, ast.Dict):
        assert len(tr.keys) == 1
        ans = format_formula(tr.keys[0], 11)+('&#8614;' if wtf == 'term' else '&#8594;')+format_formula(tr.values[0], 11)
        if rank > 11: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, ast.Num):
        return LeftSimpleExpr(str(tr.n))
    elif isinstance(tr, ast.Set):
        return '{' + ', '.join(format_formula(i, 0) for i in tr.elts) + '}'
    elif isinstance(tr, ast.IfExp):
        assert isinstance(tr.orelse, ast.Name) and tr.orelse.id == '_'
        ans = format_formula(tr.body, 0) + ' | ' + format_formula(tr.test, 0)
        if rank > 0: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, ast.BoolOp):
        op, r = OPS[type(tr.op).__name__]
        ans = op.join(format_formula(i, r) for i in tr.values)
        if r < rank: ans = SimpleExpr('('+ans+')')
        return ans
    elif isinstance(tr, (ast.List, ast.Tuple)):
        br = '[]' if isinstance(tr, ast.List) else '()'
        return br[0] + ', '.join(format_formula(i, 0) for i in tr.elts) + br[1]
    elif isinstance(tr, ast.Ellipsis):
        return '&hellip;'
    elif isinstance(tr, ast.Str):
        return html.escape(tr.s)
    elif isinstance(tr, ast.UnaryOp):
        op, r = OPS[type(tr.op).__name__]
        if isinstance(tr.op, ast.USub):
            val = format_formula(tr.operand, r)
            if isinstance(val, (LeftSimpleExpr, RightSimpleExpr, SimpleExpr)):
                ans = LeftSimpleExpr(op%val)
            else:
                ans = op%val
        ans = op%format_formula(tr.operand, r)
        if r < rank: ans = SimpleExpr('('+ans+')')
        return ans
    else: assert False, tr

def format_defs(g):
    for t, l in g:
        if l == None:
            yield (t, l)
            continue
        for i in l:
            if i['type'] == 'text' and ' $= ' in i['data']:
                l[0]['data'] = '<u>'+l[0]['data']
                i['data'] = i['data'].replace(' $= ', '</u> &mdash; ')
            elif i['type'] == 'text' and '$:' in i['data']:
                l[0]['data'] = '<u>'+l[0]['data']
                i['data'] = i['data'].replace('$:', '</u>:')
            if i['type'] == 'text':
                i['data'] = i['data'].replace('$-', '&mdash;').replace('$^', '&#8660;').replace('$&gt;', '&#8658;').replace('$&lt;', '&#8656;')
        yield (t, l)

def format_formulas(g):
    for t, l in g:
        if l == None:
            yield t
            continue
        ans = ''
        for i in l:
            if i['type'] == 'text': ans += i['data']
            elif i['type'] == 'formula':
                fm = format_formula(i['data'])
                if isinstance(i['data'], ast.Module) and len(i['data'].body) == 1 and isinstance(i['data'].body[0], ast.Expr) and isinstance(i['data'].body[0].value, ast.Tuple):
                    fm = fm[1:-1]
                ans += fm
            elif i['type'] == 'selectfile': yield ('selectfile', i['data'])
            elif i['type'] == 'pagebreak': yield '<div class="pagebreak"></div>'
        if not t.startswith('<h') and ans and ans[-1].isalnum() and l and l[-1]['type'] == 'text' and l[-1]['data']: ans += '.'
        yield t % ans

import os.path, sys

def main(src, dst, *, do_open=None):
    files = {}
    if do_open == None:
        if os.path.exists(dst):
            for i in os.listdir(dst):
                os.unlink(os.path.join(dst, i))
        else: os.mkdir(dst)
        do_open = open
    def open_file(name):
        if name in files:
            ans = files[name]
            ans.write('<hr/>\n')
            return ans
        else:
            f = do_open(os.path.join(dst, name+'.html'), 'w')
            f.write('<html>\n<head>\n<meta charset="utf-8" />\n<title>'+html.escape(name)+'</title>\n<style>\n.pagebreak\n{\n    page-break-after: always;\n}\n</style>\n</head>\n<body>\n')
            if name != 'index':
                files['index'].write('<a href="'+name+'.html">'+name+'</a>\n')
            files[name] = f
            return f
    open_file('index')
    cur_file = None
    for i in format_formulas(format_defs(parse_formulas(parse_mdlike(expand_preps(read_file(src)))))):
        print(repr(i))
        if isinstance(i, tuple) and i[0] == 'selectfile':
            cur_file = open_file(i[1])
        else:
            cur_file.write(i)
    for v in files.values():
        v.write('</body>\n</html>\n')
        v.close()

if __name__ == '__main__':
    assert len(sys.argv) == 3, "usage: nontexed <src> <dst_dir>"
    main(*sys.argv[1:])
