import py_compile, os
p = os.path.join('G:\\opencode\\RTT-Assistant', 'src', 'python', 'rtt_tool', 'ui', 'update_dialog.py')
with open(p, 'r', encoding='utf-8') as f:
    L = f.readlines()
Q=chr(34);N=chr(10);LT=chr(60);GT=chr(62);CK=chr(10003);BS=chr(92)
L[53] = '            "<p style=\\"color:#888;\\">" + i18n("label.current_version") + f" v{self._current_version}</p>")' + N
L[144] = '            self._ver_label.setText(' + N
L[145] = '                "<p style=\\"color:#00AA00; font-weight:bold;\\">" + i18n("label.new_version_found") + f" v{self._current_version}</p>")' + N
L[148] = '                "<p style=\\"color:#888;\\">" + i18n("label.current_version_latest") + f" v{self._current_version}</p>")' + N
L[159] = '                btn.setToolTip(f"{r["source"]}: {f["name"]}\n" + i18n("tooltip.click_copy_link"))' + N
with open(p, 'w', encoding='utf-8') as f:
    f.writelines(L)
py_compile.compile(p, doraise=True)
print('update_dialog.py HTML: OK')
