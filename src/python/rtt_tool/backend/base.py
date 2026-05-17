from abc import ABC, abstractmethod


class DebuggerBackend(ABC):
    """调试器后端抽象基类，定义统一的调试器操作接口。

    所有调试器实现（J-Link、PyOCD等）必须继承此类并实现所有抽象方法。
    """

    @abstractmethod
    def connect(self, device: str, interface: str = 'SWD', speed: int = 4000, **kwargs) -> bool:
        """连接调试器。

        Args:
            device: 芯片型号 (如 "STM32F407VG")
            interface: 接口类型 ("SWD" 或 "JTAG")
            speed: 通信频率 (kHz)
            **kwargs: 后端特定参数 (如 serial_number, ip_address)

        Returns:
            连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开调试器连接。"""
        pass

    @abstractmethod
    def init_rtt(self, rtt_address: int = None, rtt_mode: str = 'auto',
                 range_start: int = None, range_end: int = None) -> bool:
        """初始化 RTT 通信。

        Args:
            rtt_address: RTT 控制块地址 (仅 address 模式)
            rtt_mode: 地址获取模式 ("auto"/"address"/"range")
            range_start: 搜索范围起始地址 (仅 range 模式)
            range_end: 搜索范围结束地址 (仅 range 模式)

        Returns:
            RTT 初始化是否成功
        """
        pass

    @abstractmethod
    def rtt_read(self, channel: int = 0, buffer_size: int = 1024) -> bytes:
        """从 RTT 通道读取数据。

        Args:
            channel: RTT 通道号 (0=上行日志)
            buffer_size: 读取缓冲区大小

        Returns:
            读取到的原始字节数据
        """
        pass

    @abstractmethod
    def rtt_write(self, channel: int, data: bytes) -> int:
        """向 RTT 通道写入数据。

        Args:
            channel: RTT 通道号 (1=下行命令)
            data: 要发送的字节数据

        Returns:
            实际发送的字节数
        """
        pass

    @abstractmethod
    def get_probe_list(self) -> list:
        """获取已连接的调试器探针列表。

        Returns:
            探针信息列表，每项为 dict:
            [{"type": "jlink", "name": "J-Link (SN:1234)", "serial": "1234"}, ...]
        """
        pass

    @abstractmethod
    def read_memory(self, address: int, var_type: str = 'uint32') -> object:
        """读取目标 MCU 指定地址的内存值。

        Args:
            address: 内存地址
            var_type: 变量类型 ("uint8"/"int8"/"uint16"/"int16"/"uint32"/"int32"/"float")

        Returns:
            读取到的值
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """返回调试器连接状态。"""
        pass

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """返回后端类型标识符 (如 "jlink"/"pyocd")。"""
        pass
