import json
import os
import tempfile

import pytest
import yaml

from pydantic import ValidationError

from memos.configs.base import BaseConfig


class DummyConfig(BaseConfig):
    name: str
    value: int


def test_model_schema_override_warning(caplog):
    config = DummyConfig(name="test", value=1, model_schema="WRONG.SCHEMA")
    expected_schema = DummyConfig.__module__ + "." + DummyConfig.__qualname__
    assert config.model_schema == expected_schema
    assert "Changing schema to the default value." in caplog.text


def test_from_json_file():
    data = {"name": "from_file", "value": 42}
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    config = DummyConfig.from_json_file(tmp_path)
    assert config.name == "from_file"
    assert config.value == 42
    os.remove(tmp_path)


def test_to_json_file():
    config = DummyConfig(name="save_test", value=123)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        json_path = tmp.name

    config.to_json_file(json_path)
    with open(json_path, encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["name"] == "save_test"
    assert loaded["value"] == 123
    os.remove(json_path)


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError) as exc_info:
        DummyConfig(name="test", value=1, extra_field="not_allowed")
    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_strict_type_enforcement():
    with pytest.raises(ValidationError) as exc_info:
        DummyConfig(name="test", value="should_be_int")
    assert "value" in str(exc_info.value)


def test_from_yaml_file():
    data = {"name": "from_yaml_file", "value": 99}
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".yaml") as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = tmp.name

    config = DummyConfig.from_yaml_file(tmp_path)
    assert config.name == "from_yaml_file"
    assert config.value == 99
    os.remove(tmp_path)


def test_to_yaml_file():
    config = DummyConfig(name="yaml_save_test", value=456)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as tmp:
        yaml_path = tmp.name

    config.to_yaml_file(yaml_path)
    with open(yaml_path, encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    assert loaded["name"] == "yaml_save_test"
    assert loaded["value"] == 456
    os.remove(yaml_path)
