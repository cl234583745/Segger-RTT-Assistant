import sys

def fix_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for lineno, new_line in replacements:
        lines[lineno - 1] = new_line
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    import py_compile
    try:
        py_compile.compile(path, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f'SYNTAX ERROR: {e}')
        return False

if __name__ == '__main__':
    print('fix_util loaded')
