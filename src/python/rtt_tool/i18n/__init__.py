from PyQt5.QtCore import QObject, pyqtSignal


class _I18nManager(QObject):
    language_changed = pyqtSignal(str)

    SUPPORTED_LANGS = ("zh", "en")
    DEFAULT_LANG = "zh"

    def __init__(self, config_service=None):
        super().__init__()
        self._config_service = config_service
        self._current_lang = self.DEFAULT_LANG
        self._dicts = {}
        self._load_translations()

    def _load_translations(self):
        from .translations import BUILT_IN_TRANSLATIONS
        from .loader import TranslationLoader

        for lang in self.SUPPORTED_LANGS:
            self._dicts[lang] = {
                key: entry[lang]
                for key, entry in BUILT_IN_TRANSLATIONS.items()
                if lang in entry
            }

        loader = TranslationLoader()
        for lang in self.SUPPORTED_LANGS:
            external = loader.load_external(lang)
            if external:
                self._dicts[lang].update(external)

        if self._config_service:
            saved = self._config_service.get("language", self.DEFAULT_LANG)
            if saved in self.SUPPORTED_LANGS:
                self._current_lang = saved

    def translate(self, key):
        return self._dicts.get(self._current_lang, {}).get(key, key)

    def set_language(self, lang):
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        if lang == self._current_lang:
            return
        self._current_lang = lang
        self.language_changed.emit(lang)
        if self._config_service:
            try:
                self._config_service.set("language", lang)
                self._config_service.save()
            except Exception:
                pass

    def get_language(self):
        return self._current_lang


_instance = None


def init(config_service=None):
    global _instance
    _instance = _I18nManager(config_service)


def _(key):
    if _instance is None:
        return key
    return _instance.translate(key)


def set_language(lang):
    if _instance is not None:
        _instance.set_language(lang)


def get_language():
    if _instance is not None:
        return _instance.get_language()
    return "zh"


def language_changed():
    if _instance is not None:
        return _instance.language_changed
    return None