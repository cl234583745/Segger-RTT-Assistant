#!/usr/bin/env python3
"""初始化runtime依赖：创建venv并安装requirements.txt"""
import subprocess, sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, 'venv')
REQ_FILE = os.path.join(SCRIPT_DIR, 'requirements.txt')

def main():
    if not os.path.isfile(REQ_FILE):
        print(f'错误: {REQ_FILE} 不存在')
        return 1

    if os.path.isdir(VENV_DIR):
        print(f'venv已存在: {VENV_DIR}')
    else:
        print(f'创建venv: {VENV_DIR}')
        subprocess.run([sys.executable, '-m', 'venv', VENV_DIR], check=True)

    pip_exe = os.path.join(VENV_DIR, 'Scripts', 'pip.exe') if sys.platform == 'win32' else os.path.join(VENV_DIR, 'bin', 'pip')
    print(f'安装依赖...')
    subprocess.run([pip_exe, 'install', '-r', REQ_FILE], check=True)
    print(f'完成! 依赖已安装到 {VENV_DIR}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
