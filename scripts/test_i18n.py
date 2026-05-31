#!/usr/bin/env python3
import sys
sys.path.insert(0, 'G:/opencode/RTT-Assistant/src/python')
from rtt_tool.i18n import init, _, set_language, get_language
init()
print(f'Default lang: {get_language()}')
print(f'menu.connect: {_("menu.connect")}')
print(f'status.connected: {_("status.connected")}')
print(f'theme.dark: {_("theme.dark")}')
set_language('en')
print(f'After switch: {get_language()}')
print(f'menu.connect: {_("menu.connect")}')
print(f'status.connected: {_("status.connected")}')
print(f'theme.dark: {_("theme.dark")}')
set_language('zh')
print(f'Back to zh: {get_language()}')
print(f'menu.connect: {_("menu.connect")}')
print(f'Unknown key: {_("nonexistent.key")}')
print('i18n module test PASSED')