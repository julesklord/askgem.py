"""
Internationalization (i18n) and localization module.

Manages language detection and translation string resolution.
It does NOT manage UI layouts or rich terminal text styling.
"""

import contextlib
import json
import locale
import os
from pathlib import Path
from typing import Any, Dict


class Translator:
    """Manages multi-language translations and OS locale auto-detection.

    Attributes:
        language (str): The two-letter ISO language code currently in use.
        translations (Dict[str, str]): The loaded key-value translation map.
    """

    def __init__(self) -> None:
        """Initializes the Translator with default fallback and auto-detection."""
        self.language = "en"  # fallback
        self.translations: Dict[str, str] = {}
        self._load_translations()

    def _detect_language(self) -> str:
        """Attempts to auto-detect the system language code.

        Returns:
            str: The two-letter ISO language code (e.g. 'en', 'es').
        """
        try:
            # Check environment variables first (allows manual overwrite via LANG=es_ES)
            env_lang = os.environ.get("LANG") or os.environ.get("LC_ALL")
            if env_lang:
                return env_lang.replace("-", "_").split("_")[0][:2].lower()

            # Auto-detect using locale (e.g. ('es_ES', 'cp1252'))
            # getdefaultlocale is deprecated in 3.11+, getlocale is deprecated in 3.15+
            import sys

            if sys.version_info < (3, 11) and hasattr(locale, "getdefaultlocale"):
                sys_locale, _ = locale.getdefaultlocale()
            elif hasattr(locale, "getlocale"):
                sys_locale, _ = locale.getlocale()
            else:
                sys_locale = None

            if sys_locale:
                return sys_locale.replace("-", "_").split("_")[0][:2].lower()
        except Exception:
            pass
        return "en"

    def _load_translations(self) -> None:
        """Loads the translation JSON file corresponding to the detected locale.

        Falls back to 'en.json' if the detected language is not supported.
        """
        detected_lang = self._detect_language()

        # Resolve the absolute path of this module to find locales/
        core_dir = Path(__file__).parent.absolute()
        locales_dir = core_dir.parent / "locales"

        target_file = locales_dir / f"{detected_lang}.json"

        if target_file.exists():
            self.language = detected_lang
        else:
            target_file = locales_dir / "en.json"
            self.language = "en"

        try:
            with open(target_file, encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception:
            self.translations = {}

    def get(self, key: str, **kwargs: Any) -> str:
        """Returns the translated string, formatting with kwargs if provided.

        Args:
            key (str): The translation key to look up.
            **kwargs: Format string payload interpolation placeholders.

        Returns:
            str: The translated, formatted output string.
        """
        text = self.translations.get(key, key)
        if kwargs:
            with contextlib.suppress(KeyError):
                text = text.format(**kwargs)
        return text


# Singleton instance
_i18n = Translator()


def _(key: str, **kwargs: Any) -> str:
    """Shorthand for translation lookups.

    Args:
        key (str): The key mapping in the locales JSON target.
        **kwargs: Unpacked format dictionary mapping.

    Returns:
        str: Resolved string instance.
    """
    return _i18n.get(key, **kwargs)


def get_current_language() -> str:
    """Returns the two-letter ISO code currently in use.

    Returns:
        str: Currently loaded active locale (e.g. 'es').
    """
    return _i18n.language
