import os


class PathLinkageUtils:
    FIRMWARE_EXTENSIONS = ['.hex', '.bin', '.elf', '.srec']
    MAP_EXTENSIONS = ['.map', '.MAP']

    @staticmethod
    def search_map_file(directory: str, firmware_basename: str = '') -> str:
        if not directory or not os.path.isdir(directory):
            return ''
        try:
            entries = os.listdir(directory)
        except (OSError, PermissionError):
            return ''
        same_name_match = ''
        first_match = ''
        for entry in entries:
            name, ext = os.path.splitext(entry)
            if ext in PathLinkageUtils.MAP_EXTENSIONS:
                full_path = os.path.join(directory, entry)
                if not first_match:
                    first_match = full_path
                if firmware_basename and name == firmware_basename:
                    same_name_match = full_path
                    break
        return same_name_match or first_match

    @staticmethod
    def search_firmware_file(directory: str, hex_priority: bool = True) -> str:
        if not directory or not os.path.isdir(directory):
            return ''
        try:
            entries = os.listdir(directory)
        except (OSError, PermissionError):
            return ''
        ext_order = PathLinkageUtils.FIRMWARE_EXTENSIONS if hex_priority else list(reversed(PathLinkageUtils.FIRMWARE_EXTENSIONS))
        for target_ext in ext_order:
            for entry in entries:
                _, ext = os.path.splitext(entry)
                if ext.lower() == target_ext.lower():
                    return os.path.join(directory, entry)
        return ''

    @staticmethod
    def get_directory(filepath: str) -> str:
        if not filepath:
            return ''
        return os.path.dirname(filepath)