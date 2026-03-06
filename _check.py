import py_compile, sys
errors = []
for f in ['web/routers/marketplace.py', 'web/routers/auction.py', 'web/routers/catalog.py', 'db/models.py']:
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))

with open('web/static/js/app.js', 'r', encoding='utf-8') as fh:
    c = fh.read()
o, cl = c.count('{'), c.count('}')
po, pc = c.count('('), c.count(')')

with open('_result.txt', 'w') as out:
    out.write(f"PY errors: {len(errors)}\n")
    for e in errors:
        out.write(f"  {e}\n")
    out.write(f"JS {{{o}/{cl}}} ({po}/{pc})\n")
    out.write(f"BAL: {'YES' if o==cl and po==pc else 'NO'}\n")
    out.write(f"Lines: {c.count(chr(10))}\n")

with open('web/static/css/style.css', 'r', encoding='utf-8') as fh:
    css = fh.read()
co, cc = css.count('{'), css.count('}')
out2 = open('_result.txt', 'a')
out2.write(f"CSS {{{co}/{cc}}} BAL: {'YES' if co==cc else 'NO'}\n")
out2.close()

