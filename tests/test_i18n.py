"""
Tests for core/i18n.py — Translator and Shorthands
"""
import os
import json
from unittest.mock import patch, mock_open

from askgem.core.i18n import Translator, _, get_current_language, _i18n


class TestDetectLanguage:
    def test_detect_from_env_lang(self):
        with patch.dict(os.environ, {"LANG": "es_ES.UTF-8"}):
            translator = Translator()
            assert translator._detect_language() == "es"

    def test_detect_from_env_lc_all(self):
        with patch.dict(os.environ, {"LANG": "", "LC_ALL": "fr_FR.UTF-8"}):
            translator = Translator()
            assert translator._detect_language() == "fr"

    @patch("askgem.core.i18n.locale.getlocale")
    def test_detect_from_locale(self, mock_getlocale):
        with patch.dict(os.environ, {}, clear=True):
            mock_getlocale.return_value = ("it_IT", "cp1252")
            translator = Translator()
            assert translator._detect_language() == "it"

    @patch("askgem.core.i18n.locale.getlocale")
    def test_detect_fallback_to_en(self, mock_getlocale):
        with patch.dict(os.environ, {}, clear=True):
            mock_getlocale.return_value = (None, None)
            translator = Translator()
            assert translator._detect_language() == "en"

    @patch("askgem.core.i18n.locale.getlocale")
    def test_detect_exception_fallback_to_en(self, mock_getlocale):
        with patch.dict(os.environ, {}, clear=True):
            mock_getlocale.side_effect = Exception("Locale error")
            translator = Translator()
            assert translator._detect_language() == "en"


class TestLoadTranslations:
    @patch("askgem.core.i18n.Path.exists")
    @patch("askgem.core.i18n.Translator._detect_language")
    def test_load_translations_success(self, mock_detect, mock_exists):
        mock_detect.return_value = "es"
        mock_exists.return_value = True

        mocked_json = '{"hello": "hola"}'
        with patch("builtins.open", mock_open(read_data=mocked_json)):
            translator = Translator()

        assert translator.language == "es"
        assert translator.translations == {"hello": "hola"}

    @patch("askgem.core.i18n.Path.exists")
    @patch("askgem.core.i18n.Translator._detect_language")
    def test_load_translations_fallback_to_en(self, mock_detect, mock_exists):
        mock_detect.return_value = "es"
        mock_exists.return_value = False # es.json doesn't exist

        mocked_json = '{"hello": "hello"}'
        with patch("builtins.open", mock_open(read_data=mocked_json)):
            translator = Translator()

        assert translator.language == "en"
        assert translator.translations == {"hello": "hello"}

    @patch("askgem.core.i18n.Path.exists")
    @patch("askgem.core.i18n.Translator._detect_language")
    def test_load_translations_exception(self, mock_detect, mock_exists):
        mock_detect.return_value = "es"
        mock_exists.return_value = True

        with patch("builtins.open", mock_open(read_data="invalid json")):
            translator = Translator()

        assert translator.translations == {}


class TestGet:
    def test_get_existing_key(self):
        translator = Translator()
        translator.translations = {"hello": "hola"}
        assert translator.get("hello") == "hola"

    def test_get_missing_key_returns_key(self):
        translator = Translator()
        translator.translations = {"hello": "hola"}
        assert translator.get("goodbye") == "goodbye"

    def test_get_with_kwargs(self):
        translator = Translator()
        translator.translations = {"greeting": "Hello {name}"}
        assert translator.get("greeting", name="Alice") == "Hello Alice"

    def test_get_with_kwargs_missing_key_in_string(self):
        translator = Translator()
        translator.translations = {"greeting": "Hello"}
        assert translator.get("greeting", name="Alice") == "Hello"

    def test_get_with_missing_kwargs(self):
        translator = Translator()
        translator.translations = {"greeting": "Hello {name}"}
        assert translator.get("greeting") == "Hello {name}"

    def test_get_with_kwargs_keyerror_suppressed(self):
        translator = Translator()
        translator.translations = {"greeting": "Hello {name} {surname}"}
        assert translator.get("greeting", name="Alice") == "Hello {name} {surname}"


class TestShorthands:
    def test_underscore_shorthand(self):
        _i18n.translations = {"test_key": "test_val"}
        assert _("test_key") == "test_val"

    def test_underscore_shorthand_with_kwargs(self):
        _i18n.translations = {"test_key": "test_val {x}"}
        assert _("test_key", x="1") == "test_val 1"

    def test_get_current_language(self):
        _i18n.language = "fr"
        assert get_current_language() == "fr"
