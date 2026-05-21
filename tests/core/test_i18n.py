import os
from unittest.mock import patch

from mentask.core.i18n import Translator


def test_detect_language_env_lang():
    translator = Translator()
    with patch.dict(os.environ, {"LANG": "es_ES"}, clear=True):
        assert translator._detect_language() == "es"

def test_detect_language_env_lc_all():
    translator = Translator()
    with patch.dict(os.environ, {"LC_ALL": "fr_FR"}, clear=True):
        assert translator._detect_language() == "fr"

def test_detect_language_locale_getdefaultlocale():
    translator = Translator()
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("sys.version_info", (3, 10)),
        patch("locale.getdefaultlocale", return_value=("de_DE", "UTF-8"), create=True),
    ):
        assert translator._detect_language() == "de"

def test_detect_language_locale_getlocale():
    translator = Translator()
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("sys.version_info", (3, 11)),
        patch("locale.getlocale", return_value=("it_IT", "UTF-8"), create=True),
    ):
        assert translator._detect_language() == "it"

def test_detect_language_fallback():
    translator = Translator()
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("sys.version_info", (3, 11)),
        patch("locale.getlocale", return_value=(None, None), create=True),
    ):
        assert translator._detect_language() == "en"

def test_detect_language_exception():
    translator = Translator()
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("sys.version_info", (3, 11)),
        patch("locale.getlocale", side_effect=Exception("Test Exception"), create=True),
    ):
        assert translator._detect_language() == "en"
