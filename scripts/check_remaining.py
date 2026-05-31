#!/usr/bin/env python3
import re
with open('G:/opencode/RTT-Assistant/src/python/rtt_tool/ui/main_window.py','r',encoding='utf-8') as f:
    lines = f.readlines()
for i,line in enumerate(lines,1):
    if re.search(r'[\u4e00-\u9fff]',line):
        s = line.strip()
        if s.startswith('#') or s.startswith('"""'): continue
        if 'add_log(' in line or '_logger.' in line or 'print(' in line: continue
        if 'STYLESHEET' in line or 'setStyleSheet' in line: continue
        if 'i18n(' in line: continue
        if 'STATUS_' in line: continue
        print(f'{i}: {s[:100]}')