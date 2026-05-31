import re, os
tp = r'G:\opencode\RTT-Assistant\src\python\rtt_tool\i18n\translations.py'
tc = open(tp, 'r', encoding='utf-8').read()
dk = set(re.findall(r'"([^"]+)":\s*\{', tc))
ud = r'G:\opencode\RTT-Assistant\src\python\rtt_tool\ui'
uk = set()
for fn in os.listdir(ud):
    if fn.endswith('.py'):
        fp = os.path.join(ud, fn)
        ct = open(fp, 'r', encoding='utf-8').read()
        ks1 = re.findall(r'i18n(\("([^"]+)"', ct)
        ks2 = re.findall(r'i18n(\(''([^']+)''', ct)
        uk.update(ks1)
        uk.update(ks2)
m = uk - dk
if m:
    print('Missing (' + str(len(m)) + '):')
    for k in sorted(m):
        print('  ' + k)
else:
    print('All keys defined!')
