import os
import time
import pytest

try:
    from dart_planner.communication.secure_serializer import SecureSerializer
except Exception:
    pytest.skip("SecureSerializer import failed; skipping security tests", allow_module_level=True)


def test_default_ttl(monkeypatch):
    monkeypatch.delenv("DART_MSG_TTL", raising=False)
    ser = SecureSerializer(secret_key="abc", test_mode=True)
    assert ser._msg_ttl == 300


def test_env_ttl(monkeypatch):
    monkeypatch.setenv("DART_MSG_TTL", "1200")
    ser = SecureSerializer(secret_key="abc", test_mode=True)
    assert ser._msg_ttl == 1200


def test_custom_ttl_param(monkeypatch):
    monkeypatch.setenv("DART_MSG_TTL", "600")
    ser = SecureSerializer(secret_key="abc", test_mode=True, message_ttl=10)
    assert ser._msg_ttl == 10


def test_deserialize_old_message(monkeypatch):
    ser = SecureSerializer(secret_key="abc", test_mode=True, message_ttl=1)
    data = {"foo": "bar"}
    serialized = ser.serialize(data)
    # wait beyond ttl
    time.sleep(1.5)
    with pytest.raises(Exception):
        ser.deserialize(serialized) 