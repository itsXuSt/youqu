import pytest


class TestVLMConfig:
    def test_enabled_default_false(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.enabled is False

    def test_enabled_env_override(self, monkeypatch):
        monkeypatch.setenv("YOUQU_VLM_ENABLED", "true")
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.enabled is True

    def test_enabled_env_override_1(self, monkeypatch):
        monkeypatch.setenv("YOUQU_VLM_ENABLED", "1")
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.enabled is True

    def test_enabled_env_override_yes(self, monkeypatch):
        monkeypatch.setenv("YOUQU_VLM_ENABLED", "yes")
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.enabled is True

    def test_enabled_env_override_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("YOUQU_VLM_ENABLED", "True")
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.enabled is True

    def test_backend_base_url(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.backend.base_url == "https://api-inference.modelscope.cn/v1/"

    def test_backend_model(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.backend.model == "Qwen/Qwen3-VL-8B-Instruct"

    def test_backend_api_key(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.backend.api_key.startswith("ms-")

    def test_backend_timeout_is_int(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.backend.timeout, int)
        assert config.backend.timeout == 30

    def test_backend_max_retries_is_int(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.backend.max_retries, int)
        assert config.backend.max_retries == 3

    def test_backend_retry_delay_is_int(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.backend.retry_delay, int)
        assert config.backend.retry_delay == 1

    def test_backend_max_image_dim_is_int(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.backend.max_image_dim, int)
        assert config.backend.max_image_dim == 2048

    def test_fallback_confidence_threshold_is_float(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.fallback.confidence_threshold, float)
        assert 0.0 <= config.fallback.confidence_threshold <= 1.0

    def test_max_iterations_is_int(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert isinstance(config.max_iterations, int)
        assert config.max_iterations == 20

    def test_evidence_dir_is_path(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        from pathlib import Path

        assert isinstance(config.evidence_dir, Path)
        assert config.evidence_dir.exists()

    def test_is_available_false_when_disabled(self, monkeypatch):
        monkeypatch.delenv("YOUQU_VLM_ENABLED", raising=False)
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        assert config.is_available() is False

    def test_is_available_true_when_enabled(self, monkeypatch):
        monkeypatch.setenv("YOUQU_VLM_ENABLED", "true")
        from src.vlm.config import VLMConfig

        config = VLMConfig()
        result = config.is_available()
        assert result is True
