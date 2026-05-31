import os
import time
from typing import Callable
from .flash_base import BaseFlashBackend
from ..models.flash_params import FlashParams
from ..models.flash_result import FlashResult


class JLinkFlashBackend(BaseFlashBackend):

    @property
    def backend_type(self) -> str:
        return 'jlink'

    def flash(self, params: FlashParams, progress_callback: Callable[[str], None]) -> FlashResult:
        start_time = time.strftime('%Y-%m-%dT%H:%M:%S')
        log_lines = []

        def _log(msg: str):
            log_lines.append(msg)
            try:
                progress_callback(msg)
            except Exception:
                pass

        _log(f"[JLink] 烧录参数: firmware={params.firmware_path}, chip={params.chip_model}, "
             f"interface={params.interface}, speed={params.speed}, serial={params.serial_number}")

        try:
            import pylink
            from pylink import library
        except ImportError:
            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
            return FlashResult(
                status='failure', firmware_path=params.firmware_path,
                debugger_type='jlink', chip_model=params.chip_model,
                start_time=start_time, end_time=end_time,
                error_message='pylink库未安装，无法使用J-Link烧录',
                log_output='\n'.join(log_lines),
            )

        jlink = None
        try:
            jlink_path = params.jlink_path if hasattr(params, 'jlink_path') and params.jlink_path else None
            if jlink_path:
                jlink_lib = library.Library(dllpath=jlink_path)
            else:
                jlink_lib = library.Library()
            jlink = pylink.JLink(lib=jlink_lib)
            _log("[JLink] JLink实例创建成功")

            if params.serial_number:
                _log(f"[JLink] jlink.open(serial_no={params.serial_number})")
                jlink.open(serial_no=params.serial_number)
            else:
                try:
                    num = jlink.num_connected_emulators()
                except Exception:
                    num = 0
                if num == 0:
                    raise RuntimeError("未检测到J-Link探针，请先连接探针")
                _log(f"[JLink] jlink.open() (检测到{num}个探针)")
                jlink.open()

            try:
                jlink.disable_dialog_boxes()
            except Exception:
                pass

            interface_map = {'SWD': pylink.enums.JLinkInterfaces.SWD, 'JTAG': pylink.enums.JLinkInterfaces.JTAG}
            iface = interface_map.get(params.interface.upper(), pylink.enums.JLinkInterfaces.SWD)
            _log(f"[JLink] jlink.set_tif({iface})")
            jlink.set_tif(iface)

            _log(f"[JLink] jlink.connect(chip_name='{params.chip_model}', speed={params.speed})")
            jlink.connect(chip_name=params.chip_model, speed=params.speed)

            try:
                core_info = jlink.core_info()
                _log(f"[JLink] 核心信息: {core_info}")
            except Exception:
                pass

            try:
                num_flash = jlink.num_flash_blocks()
                _log(f"[JLink] Flash块数: {num_flash}")
                if num_flash > 0:
                    for i in range(num_flash):
                        try:
                            fb = jlink.flash_block_info(i)
                            _log(f"[JLink] Flash块{i}: addr=0x{fb.Addr:X}, size=0x{fb.Size:X}")
                        except Exception:
                            pass
                else:
                    _log("[JLink] 警告: 未检测到Flash块! 芯片型号可能不正确，无法加载Flash算法")
            except Exception as e:
                _log(f"[JLink] 获取Flash信息失败: {e}")

            _log(f"[JLink] jlink.flash_file('{params.firmware_path}', addr=0)")

            def _on_progress(action, progress_str, percentage):
                action_str = action.decode() if isinstance(action, bytes) else str(action)
                progress_str_clean = progress_str.decode() if isinstance(progress_str, bytes) else str(progress_str or '')
                _log(f"  [{action_str}] {progress_str_clean} ({percentage}%)")

            result = jlink.flash_file(params.firmware_path, addr=0, on_progress=_on_progress)
            _log(f"[JLink] flash_file返回值: {result} (>=0表示成功)")

            _log("[JLink] jlink.reset()")
            jlink.reset()

            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
            return FlashResult(
                status='success', firmware_path=params.firmware_path,
                debugger_type='jlink', chip_model=params.chip_model,
                start_time=start_time, end_time=end_time,
                log_output='\n'.join(log_lines),
            )

        except Exception as e:
            end_time = time.strftime('%Y-%m-%dT%H:%M:%S')
            err_msg = str(e)
            _log(f"[JLink] 烧录错误: {err_msg}")
            return FlashResult(
                status='failure', firmware_path=params.firmware_path,
                debugger_type='jlink', chip_model=params.chip_model,
                start_time=start_time, end_time=end_time,
                error_message=err_msg, log_output='\n'.join(log_lines),
            )
        finally:
            if jlink:
                try:
                    jlink.close()
                except Exception:
                    pass
