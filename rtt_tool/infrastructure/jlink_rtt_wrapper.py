#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JLink RTT SDK封装
使用pylink库实现RTT功能
"""

import os
import sys
import struct
import pylink
from pylink import library


class JLinkRTTWrapper:
    """JLink RTT SDK封装类"""
    
    def __init__(self, jlink_path=None):
        """
        初始化JLink RTT封装
        
        Args:
            jlink_path: JLink安装路径，None则自动查找
        """
        self.jlink = None
        self.connected = False
        self.rtt_initialized = False
        
        # 查找JLinkARM.dll
        if jlink_path is None:
            jlink_path = self._find_jlink_dll()
        
        if jlink_path is None:
            raise RuntimeError(
                "未找到JLinkARM.dll，请安装JLink软件或指定路径。\n"
                "注意: JLink DLL位数必须与Python位数匹配!\n"
                f"当前Python: {struct.calcsize('P') * 8}位"
            )
        
        self.jlink_path = jlink_path
        
        # 检查DLL位数
        try:
            import pefile
            pe = pefile.PE(jlink_path)
            dll_bits = 64 if pe.OPTIONAL_HEADER.Magic == 0x20b else 32
            python_bits = struct.calcsize('P') * 8
            
            if dll_bits != python_bits:
                raise RuntimeError(
                    f"JLink DLL位数不匹配!\n"
                    f"JLink DLL: {dll_bits}位\n"
                    f"Python: {python_bits}位\n"
                    f"请安装{'64位' if python_bits == 64 else '32位'}版本的JLink软件"
                )
        except ImportError:
            # pefile未安装,跳过检查
            pass
        except Exception:
            # 其他错误,跳过检查
            pass
        
        # 设置环境变量，让pylink找到DLL
        jlink_dir = os.path.dirname(jlink_path)
        os.environ['JLINK_PATH'] = jlink_dir
        
        # 将JLink目录添加到PATH环境变量
        if jlink_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = jlink_dir + os.pathsep + os.environ.get('PATH', '')
    
    def _find_jlink_dll(self):
        """
        自动查找JLinkARM.dll
        
        Returns:
            str: DLL路径，未找到返回None
        """
        # 检查Python位数
        python_bits = struct.calcsize('P') * 8
        
        # 根据Python位数选择DLL名称
        dll_name = "JLink_x64.dll" if python_bits == 64 else "JLinkARM.dll"
        
        # 打包环境下获取基础目录
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            try:
                meipass_dir = sys._MEIPASS
            except AttributeError:
                meipass_dir = exe_dir
        else:
            exe_dir = None
            meipass_dir = None
        
        # 常见JLink安装路径
        possible_paths = [
            # 当前目录(优先)
            os.path.join(os.getcwd(), dll_name),
            # 打包后exe所在目录
            os.path.join(exe_dir, dll_name) if exe_dir else None,
            # 打包后_MEIPASS目录
            os.path.join(meipass_dir, dll_name) if meipass_dir else None,
            # V938a (支持64位)
            rf"D:\Program Files\SEGGER\JLink_V938a\{dll_name}",
            rf"C:\Program Files\SEGGER\JLink_V938a\{dll_name}",
            # V930
            rf"D:\Program Files\SEGGER\JLink_V930\{dll_name}",
            rf"C:\Program Files\SEGGER\JLink_V930\{dll_name}",
            rf"C:\Program Files (x86)\SEGGER\JLink_V930\{dll_name}",
            # V940
            rf"D:\Program Files\SEGGER\JLink_V940\{dll_name}",
            rf"C:\Program Files\SEGGER\JLink_V940\{dll_name}",
            rf"C:\Program Files (x86)\SEGGER\JLink_V940\{dll_name}",
            # V950
            rf"D:\Program Files\SEGGER\JLink_V950\{dll_name}",
            rf"C:\Program Files\SEGGER\JLink_V950\{dll_name}",
            rf"C:\Program Files (x86)\SEGGER\JLink_V950\{dll_name}",
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        # 尝试在PATH环境变量中查找
        path_env = os.environ.get('PATH', '')
        for path_dir in path_env.split(os.pathsep):
            dll_path = os.path.join(path_dir, dll_name)
            if os.path.exists(dll_path):
                return dll_path
        
        return None
    
    def connect(self, device="Cortex-M4", interface="SWD", speed=4000, 
                serial_number=None, ip_address=None, rtt_address=None):
        """
        连接到MCU
        
        Args:
            device: MCU型号，如"Cortex-M4"
            interface: 接口类型，"SWD"或"JTAG"
            speed: 接口速度（kHz）
            serial_number: JLink序列号（可选）
            ip_address: JLink IP地址（可选）
            rtt_address: RTT控制块地址（可选）
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True
        
        try:
            # 创建JLink库对象
            jlink_lib = library.Library(dllpath=self.jlink_path)
            
            # 创建JLink对象
            self.jlink = pylink.JLink(lib=jlink_lib)
            
            # 打开JLink
            if serial_number:
                self.jlink.open(serial_no=serial_number)
            elif ip_address:
                self.jlink.open(ip_addr=ip_address)
            else:
                self.jlink.open()
            
            # 选择接口
            if interface.upper() == "SWD":
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
            else:
                self.jlink.set_tif(pylink.enums.JLinkInterfaces.JTAG)
            
            # 连接(传入设备型号和速度)
            self.jlink.connect(chip_name=device, speed=speed)
            
            self.connected = True
            return True
            
        except Exception as e:
            self.connected = False
            if self.jlink:
                try:
                    self.jlink.close()
                except:
                    pass
                self.jlink = None
            raise RuntimeError(f"连接失败: {e}")
    
    def disconnect(self):
        """断开连接"""
        if not self.connected:
            return
        
        try:
            if self.jlink:
                self.jlink.close()
        except:
            pass
        
        self.connected = False
        self.rtt_initialized = False
        self.jlink = None
    
    def init_rtt(self, rtt_address=None):
        """
        初始化RTT
        
        Args:
            rtt_address: RTT控制块地址（可选）
        
        Returns:
            bool: 初始化是否成功
        """
        if not self.connected:
            raise RuntimeError("未连接到MCU")
        
        if self.rtt_initialized:
            return True
        
        try:
            # 启动RTT
            if rtt_address:
                # 指定地址
                self.jlink.rtt_start(rtt_address)
            else:
                # 自动检测
                self.jlink.rtt_start()
            
            self.rtt_initialized = True
            return True
            
        except Exception as e:
            self.rtt_initialized = False
            raise RuntimeError(f"RTT初始化失败: {e}")
    
    def read_rtt(self, buffer_size=1024, channel=0):
        """
        从RTT读取数据
        
        Args:
            buffer_size: 读取缓冲区大小
            channel: RTT通道号
        
        Returns:
            bytes: 读取的数据
        """
        if not self.rtt_initialized:
            raise RuntimeError("RTT未初始化")
        
        try:
            # 读取数据
            data = self.jlink.rtt_read(channel, buffer_size)
            return bytes(data)
        except Exception as e:
            raise RuntimeError(f"RTT读取失败: {e}")
    
    def write_rtt(self, data, channel=0):
        """
        向RTT写入数据
        
        Args:
            data: 要写入的数据（bytes）
            channel: RTT通道号
        
        Returns:
            int: 实际写入的字节数
        """
        if not self.rtt_initialized:
            raise RuntimeError("RTT未初始化")
        
        if not data:
            return 0
        
        try:
            # 写入数据
            num_bytes = self.jlink.rtt_write(channel, list(data))
            return num_bytes
        except Exception as e:
            raise RuntimeError(f"RTT写入失败: {e}")
    
    def __del__(self):
        """析构函数，确保断开连接"""
        self.disconnect()
