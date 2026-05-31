import py_compile, sys, os
path = sys.argv[1]
rules_file = sys.argv[2]
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
exec(open(rules_file, 'r', encoding='utf-8').read())
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
py_compile.compile(path, doraise=True)
print('OK')
