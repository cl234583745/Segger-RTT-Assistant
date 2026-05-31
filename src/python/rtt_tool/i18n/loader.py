import json
import os
import logging

_logger = logging.getLogger(__name__)


class TranslationLoader:
    def load_external(self, lang, base_dir=None):
        if base_dir is None:
            from ..utils.resource_utils import get_exe_dir, get_base_dir, is_frozen
            if is_frozen():
                exe_dir = get_exe_dir()
                external_dir = os.path.join(exe_dir, "config", "i18n")
                if os.path.isdir(external_dir):
                    base_dir = exe_dir
                else:
                    base_dir = get_base_dir()
            else:
                base_dir = get_exe_dir()

        filepath = os.path.join(base_dir, "config", "i18n", f"{lang}.json")

        if not os.path.exists(filepath):
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                _logger.warning(f"翻译文件格式错误(非字典): {filepath}")
                return {}
            return {k: str(v) for k, v in data.items() if isinstance(k, str)}

        except json.JSONDecodeError as e:
            _logger.warning(f"翻译文件JSON格式错误: {filepath}, 行{e.lineno}")
            return {}
        except UnicodeDecodeError:
            _logger.warning(f"翻译文件编码错误(需UTF-8): {filepath}")
            return {}
        except Exception as e:
            _logger.warning(f"翻译文件加载失败: {filepath}, {e}")
            return {}