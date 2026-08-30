"""Logging redaction tests — no secret ever reaches logs."""

from asguard.logging_setup import redact_secrets


def test_openai_key_redacted():
    assert "sk-real-secret-abc123" not in redact_secrets("call failed with key sk-real-secret-abc123")
    assert "[REDACTED]" in redact_secrets("key sk-real-secret-abc123")


def test_bearer_token_redacted():
    assert "abcdefghijklmnop" not in redact_secrets("Authorization: Bearer abcdefghijklmnop123456")


def test_password_field_redacted():
    assert "hunter2" not in redact_secrets("password: hunter2")


def test_normal_text_untouched():
    text = "user asked about the project status"
    assert redact_secrets(text) == text
