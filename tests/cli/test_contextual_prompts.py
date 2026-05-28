import tempfile
from pathlib import Path

from mentask.cli.contextual_prompts import (
    ContextType,
    ContextualConfigManager,
    ContextualPromptLibrary,
)
from mentask.cli.themes import get_theme


class TestContextualPrompts:
    def test_get_context_prompt(self):
        """Test obtener prompt por contexto."""
        prompt = ContextualPromptLibrary.get(ContextType.CODING)
        assert prompt.context == ContextType.CODING
        assert "KISS" in prompt.system_prompt or "engineering" in prompt.system_prompt.lower()

    def test_get_adapted_prompt(self):
        """Test adaptación por modelo."""
        prompt = ContextualPromptLibrary.get_adapted(ContextType.MUSIC_PRODUCTION, "claude")
        assert "producer" in prompt.lower() or "audio" in prompt.lower()

    def test_integrated_neon_theme_get(self):
        """Test que los temas neon ahora están integrados en el sistema estándar."""
        theme = get_theme("neon_pink")
        assert theme.brand_primary == "#ff006e"

    def test_contextual_config_persistence(self):
        """Test persistencia de config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ContextualConfigManager(Path(tmpdir))
            config.set_context(ContextType.MUSIC_PRODUCTION)

            # Crear nueva instancia, debe cargar cambio
            config2 = ContextualConfigManager(Path(tmpdir))
            assert config2.get_active_context() == ContextType.MUSIC_PRODUCTION
