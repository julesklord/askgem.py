import json
from unittest.mock import patch

import pytest

from mentask.agent.core.simulation import SimulatedChunk, SimulationManager


class TestSimulationManager:
    @pytest.fixture
    def transcript_file(self, tmp_path):
        return tmp_path / "transcript.json"

    def test_load_valid_transcript(self, transcript_file):
        data = {"hello": [[{"text": "hi", "function_calls": [], "usage": {}}]]}
        transcript_file.write_text(json.dumps(data))

        manager = SimulationManager(str(transcript_file), mode="playback")

        assert "hello" in manager.transcripts
        assert len(manager.transcripts["hello"]) == 1
        chunk = manager.transcripts["hello"][0][0]
        assert isinstance(chunk, SimulatedChunk)
        assert chunk.text == "hi"

    def test_load_file_not_found(self, transcript_file):
        # SimulationManager.__init__ only calls load() if os.path.exists(transcript_path)
        # So we instantiate it first (it won't call load because file doesn't exist)
        manager = SimulationManager(str(transcript_file), mode="playback")

        with patch("mentask.agent.core.simulation._logger") as mock_logger:
            # Manually call load to trigger the error path for open()
            manager.load()
            mock_logger.error.assert_called()
            assert "Failed to load simulation transcript" in mock_logger.error.call_args[0][0]

    def test_load_invalid_json(self, transcript_file):
        transcript_file.write_text("not json")

        with patch("mentask.agent.core.simulation._logger") as mock_logger:
            # __init__ calls load() because the file exists
            SimulationManager(str(transcript_file), mode="playback")
            mock_logger.error.assert_called()
            assert "Failed to load simulation transcript" in mock_logger.error.call_args[0][0]

    def test_load_malformed_data(self, transcript_file):
        # SimulatedChunk constructor will fail if data doesn't match dataclass fields
        data = {"hello": [[{"wrong_key": "val"}]]}
        transcript_file.write_text(json.dumps(data))

        with patch("mentask.agent.core.simulation._logger") as mock_logger:
            SimulationManager(str(transcript_file), mode="playback")
            mock_logger.error.assert_called()
            assert "Failed to load simulation transcript" in mock_logger.error.call_args[0][0]
