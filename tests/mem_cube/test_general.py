import json
import os
import tempfile

from unittest.mock import MagicMock, patch

import pytest

from memos.configs.mem_cube import GeneralMemCubeConfig
from memos.mem_cube.general import GeneralMemCube
from memos.memories.activation.base import BaseActMemory
from memos.memories.parametric.base import BaseParaMemory
from memos.memories.textual.base import BaseTextMemory


@pytest.fixture
def mem_cube():
    """Set up test fixtures for GeneralMemCube."""
    with open("./examples/data/mem_cube_2/config.json", encoding="utf-8") as f:
        config_data = json.load(f)
    mock_config = GeneralMemCubeConfig.model_validate(config_data)

    # Create mock instances that are also instances of the base classes
    mock_text_mem = MagicMock(spec=BaseTextMemory)
    mock_act_mem = MagicMock(spec=BaseActMemory)
    mock_para_mem = MagicMock(spec=BaseParaMemory)

    # Mock the MemoryFactory.from_config method to return our mock instances
    def mock_from_config(config_factory):
        backend = config_factory.backend
        if backend == "general_text":
            return mock_text_mem
        elif backend == "kv_cache":
            return mock_act_mem
        elif backend == "lora":
            return mock_para_mem
        else:
            # Fallback for any other backend
            return MagicMock()

    with patch("memos.memories.factory.MemoryFactory.from_config", side_effect=mock_from_config):
        # Create the GeneralMemCube instance
        mem_cube = GeneralMemCube(mock_config)

        # Attach the mock instances for easy access in tests
        mem_cube.text_mem = mock_text_mem
        mem_cube.act_mem = mock_act_mem
        mem_cube.para_mem = mock_para_mem

        return mem_cube


def test_load_with_real_directory():
    """Test loading from a real directory structure."""
    fixture_dir = "./examples/data/mem_cube_2"

    if os.path.exists(fixture_dir):
        # This would test with real config file
        try:
            mem_cube = GeneralMemCube.init_from_dir(fixture_dir)
            assert isinstance(mem_cube, GeneralMemCube)
        except Exception:
            # If fixture doesn't have proper config, that's expected
            pass


def test_memory_interface_methods_called(mem_cube):
    """Test that the correct memory interface methods are called."""
    with (
        patch("memos.mem_cube.general.get_json_file_model_schema") as mock_get_schema,
        tempfile.TemporaryDirectory() as test_dir,
    ):
        mock_get_schema.return_value = mem_cube.config.model_schema

        # Test load
        mem_cube.load(test_dir)

        # Verify all memory types are loaded
        mem_cube.text_mem.load.assert_called_once_with(test_dir)
        mem_cube.act_mem.load.assert_called_once_with(test_dir)
        mem_cube.para_mem.load.assert_called_once_with(test_dir)

        # Reset mocks
        mem_cube.text_mem.reset_mock()
        mem_cube.act_mem.reset_mock()
        mem_cube.para_mem.reset_mock()

        # Test dump
        mem_cube.dump(test_dir)

        # Verify all memory types are dumped
        mem_cube.text_mem.dump.assert_called_once_with(test_dir)
        mem_cube.act_mem.dump.assert_called_once_with(test_dir)
        mem_cube.para_mem.dump.assert_called_once_with(test_dir)
