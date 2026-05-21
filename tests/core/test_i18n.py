import os
import sys
from unittest.mock import patch
import locale
import pytest

from mentask.core.i18n import Translator

def test_detect_language_exception_fallback():
    """Test that _detect_language safely falls back to 'en' when an exception is raised."""
    translator = Translator()

    with patch.dict(os.environ, {}, clear=True):
        with patch('locale.getdefaultlocale', side_effect=Exception("Test Exception")), \
             patch('locale.getlocale', side_effect=Exception("Test Exception")):

            lang = translator._detect_language()
            assert lang == "en"
