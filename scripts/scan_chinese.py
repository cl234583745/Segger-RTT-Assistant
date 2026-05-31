#!/usr/bin/env python3
"""Scan all UI Python files for remaining hardcoded Chinese text."""
import re, os

ui_dir = 'G:/opencode/RTT-Assistant/src/python/rtt_tool/ui'
ctrl_dir = 'G:/opencode/RTT-Assistant/src/python/rtt_tool/controller'

for root in [ui_dir, ctrl_dir]:
    for fname in sorted(os.listdir(root)):
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        issues = []
        for i, line in enumerate(lines, 1):
            if not re.search(r'[\u4e00-\u9fff]', line):
                continue
            s = line.strip()
            if s.startswith('#') or s.startswith('"""') or s.startswith("'''"):
                continue
            if 'add_log(' in line or '_logger.' in line or 'print(' in line:
                continue
            if 'STYLESHEET' in line or 'setStyleSheet' in line:
                continue
            if 'i18n(' in line:
                continue
            if 'STATUS_' in line:
                continue
            if 'BUILT_IN_TRANSLATIONS' in line:
                continue
            issues.append((i, s[:120]))
        if issues:
            print(f"\n=== {fname} ({len(issues)} issues) ===")
            for lineno, text in issues:
                print(f"  {lineno}: {text}")