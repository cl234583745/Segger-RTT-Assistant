import sys
import os
import time
import subprocess
from typing import Callable
from .flash_base import BaseFlashBackend
from ..models.flash_params import FlashParams
from ..models.flash_result import FlashResult


class PyocdFlashBackend(BaseFlashBackend):

    @property
    def backend_type(self) -> str:
        return 'pyocd'

    def flash(self, params: FlashParams, progress_callback: Callable[[str], None]) -> FlashResult:
        start_time = time.strftime('%Y-%m-%dT%H:%M:%S')
        log_lines = []

        def _log(msg: str):
            log_lines.append(msg)
            try:
                progress_callback(msg)
            except Exception:
                pass

        target = params.pyocd_target or params.chip_model
        frequency_hz = params.speed * 1000

        try:
            from ..utils.resource_utils import is_frozen, get_exe_dir
        except Exception:
            is_frozen = lambda: False
            get_exe_dir = lambda: ''

        pyocd_exe = None
        pack_files = []

        if is_frozen():
            standalone_pyocd = os.path.join(get_exe_dir(), 'runtime', 'pyocd', 'pyocd.exe')
            if os.path.isfile(standalone_pyocd):
                pyocd_exe = standalone_pyocd
                packs_dir = os.path.join(get_exe_dir(), 'runtime', 'packs')
                if os.path.isdir(packs_dir):
                    import glob as _glob
                    pack_files = sorted(_glob.glob(os.path.join(packs_dir, '*.pack')))

        firmware_path = params.firmware_path
        firmware_ext = os.path.splitext(firmware_path)[1].lower()
        if firmware_ext == '.srec':
            elf_path = os.path.splitext(firmware_path)[0] + '.elf'
            if os.path.isfile(elf_path):
                _log(f"[PyOCD] .srec不被pyocd支持，自动替换为.elf: {elf_path}")
                firmware_path = elf_path
            else:
                hex_path = os.path.splitext(firmware_path)[0] + '.hex'
                if os.path.isfile(hex_path):
                    _log(f"[PyOCD] .srec不被pyocd支持，自动替换为.hex: {hex_path}")
                    firmware_path = hex_path
                else:
                    end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
                    err_msg = f"pyocd不支持.srec格式，且未找到同名.elf或.hex文件"
                    _log(f"[PyOCD] 错误: {err_msg}")
                    return FlashResult(
                        status='failure', firmware_path=params.firmware_path,
                        debugger_type=params.debugger_type, chip_model=params.chip_model,
                        start_time=start_time, end_time=end_time,
                        error_message=err_msg, log_output='\n'.join(log_lines),
                    )

        if pyocd_exe:
            cmd = [
                pyocd_exe, 'flash',
                '--target', target,
                '--erase', 'auto',
                '--frequency', str(frequency_hz),
            ]
            for pf in pack_files:
                cmd.extend(['--pack', pf])
        else:
            cmd = [
                sys.executable, '-m', 'pyocd', 'flash',
                '--target', target,
                '--erase', 'auto',
                '--frequency', str(frequency_hz),
            ]
        if params.serial_number:
            cmd.extend(['--probe', params.serial_number])
        cmd.append(firmware_path)

        _log(f"[PyOCD] 烧录参数: target={target}, frequency={frequency_hz}Hz, "
             f"probe={params.serial_number}, firmware={params.firmware_path}")
        _log(f"[PyOCD] 执行命令: {' '.join(cmd)}")

        try:
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creationflags,
            )

            for line in proc.stdout:
                stripped = line.rstrip()
                if stripped:
                    _log(stripped)

            proc.wait()
            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')

            if proc.returncode == 0:
                return FlashResult(
                    status='success', firmware_path=params.firmware_path,
                    debugger_type=params.debugger_type, chip_model=params.chip_model,
                    start_time=start_time, end_time=end_time,
                    log_output='\n'.join(log_lines),
                )
            else:
                err_msg = f"pyocd返回非零退出码: {proc.returncode}"
                return FlashResult(
                    status='failure', firmware_path=params.firmware_path,
                    debugger_type=params.debugger_type, chip_model=params.chip_model,
                    start_time=start_time, end_time=end_time,
                    error_message=err_msg, log_output='\n'.join(log_lines),
                )

        except FileNotFoundError:
            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
            err_msg = 'pyocd未安装或不在PATH中'
            _log(f"[PyOCD] 错误: {err_msg}")
            return FlashResult(
                status='failure', firmware_path=params.firmware_path,
                debugger_type=params.debugger_type, chip_model=params.chip_model,
                start_time=start_time, end_time=end_time,
                error_message=err_msg, log_output='\n'.join(log_lines),
            )
        except Exception as e:
            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
            err_msg = str(e)
            _log(f"[PyOCD] 烧录错误: {err_msg}")
            return FlashResult(
                status='failure', firmware_path=params.firmware_path,
                debugger_type=params.debugger_type, chip_model=params.chip_model,
                start_time=start_time, end_time=end_time,
                error_message=err_msg, log_output='\n'.join(log_lines),
            )
