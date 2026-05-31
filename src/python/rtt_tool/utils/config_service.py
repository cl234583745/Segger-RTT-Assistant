import json
import os
import copy
from .resource_utils import get_exe_dir


def _build_default_channel_configs():
    from ..models.channel_config import DEFAULT_CHANNEL_COLORS
    configs = {}
    for ch in range(1, 11):
        configs[str(ch)] = {
            'color': DEFAULT_CHANNEL_COLORS[(ch - 1) % len(DEFAULT_CHANNEL_COLORS)],
            'style': 0,
            'vdiv': 1.0,
            'yoffset': 0.0,
            'enabled': ch == 1,
        }
    return configs


class ConfigService:

    DEFAULT_CONFIG = {
        "device": "Cortex-M4",
        "interface": "SWD",
        "speed": 4000,
        "jlink_path": None,
        "show_timestamp": False,
        "hex_display": False,
        "hex_send": False,
        "add_newline": True,
        "window_topmost": False,
        "font_family": "Courier New",
        "font_size": 10,
        "window_width": 1200,
        "window_height": 800,
        "window_x": None,
        "window_y": None,
        "window_maximized": False,
        "window_state": None,
        "rtt_address": "",
        "last_device": "Cortex-M4",
        "last_serial_number": None,
        "rtt_mode": "auto",
        "rtt_range_start": "",
        "rtt_range_size": "",
        "map_file_path": "",
        "ansi_color_enabled": False,
        "keyword_highlight_enabled": True,
        "keyword_rules": {
            "ERROR": "#ff0000",
            "WARN": "#ffff00",
            "WARNING": "#ffff00",
            "FAIL": "#ff0000",
            "OK": "#00ff00",
            "SUCCESS": "#00ff00",
        },
        "debugger_type": "jlink",
        "poll_interval": 10,
        "display_mode": "log",
        "time_base": 100,
        "trigger_mode": "auto",
        "trigger_channel": 0,
        "trigger_edge": "rising",
        "vertical_scale": "auto",
        "color_theme": "dark",
        "waveform_channels": [1],
        "monitor_interval": 100,
        "monitored_variables": [],
        "ring_buffer_size": 65536,
        "ring_buffer_full_log_level": "DEBUG",
        "log_level.rtt_system": "INFO",
        "log_level.pyocd_diag": "INFO",
        "log_level.rtt_debug": "INFO",
        "language": "zh",
        "scope_view_mode": "oscilloscope",
        "channel_configs": None,
        "sub_channel_configs": {},
        "firmware_paths": [],
        "active_firmware_index": -1,
    }

    def __init__(self, config_file=None):
        if config_file is None:
            from ..runtime.path_config import RUNTIME_CONFIG_JSON
            config_file = RUNTIME_CONFIG_JSON
        self.config_file = config_file
        self.config = {}
        self.load()

    def _ensure_defaults(self):
        if self.config.get('channel_configs') is None:
            self.config['channel_configs'] = _build_default_channel_configs()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
                self._ensure_defaults()
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.config = copy.deepcopy(self.DEFAULT_CONFIG)
                self._ensure_defaults()
        else:
            self.config = copy.deepcopy(self.DEFAULT_CONFIG)
            self._ensure_defaults()
        self.save()

    def save(self):
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reset_to_default(self):
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._ensure_defaults()
        self.save()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def get_all(self):
        return self.config.copy()

    def set_all(self, config):
        self.config.update(config)
