"""Sanitizer unit tests — prove secrets are actually removed."""

from asguard.output_guard.detectors import ApiKeyDetector
from asguard.output_guard.pii_detectors import EmailDetector
from asguard.output_guard.sanitizer import Sanitizer
from asguard.security_models.enums import PolicyAction


def test_api_key_removed_by_redact():
    text = "Here is your API key: sk-example-secret-000111222333 please use it."
    detected = ApiKeyDetector().detect(text)
    assert detected.detected
    result = Sanitizer().sanitize(text, detected.spans, PolicyAction.REDACT)
    assert "sk-example-secret-000111222333" not in result.sanitized_text
    assert "[REDACTED:API_KEY]" in result.sanitized_text
    assert result.verified_clean


def test_api_key_removed_by_sanitize():
    text = "API key: sk-example-secret-000111222333"
    detected = ApiKeyDetector().detect(text)
    result = Sanitizer().sanitize(text, detected.spans, PolicyAction.SANITIZE)
    assert "sk-example" not in result.sanitized_text
    assert "API key" in result.sanitized_text
    assert result.verified_clean


def test_email_removed():
    text = "Contact admin@example-corp.com for help."
    detected = EmailDetector().detect(text)
    result = Sanitizer().sanitize(text, detected.spans, PolicyAction.SANITIZE)
    assert "admin@example-corp.com" not in result.sanitized_text
    assert "Contact" in result.sanitized_text and "for help." in result.sanitized_text
    assert result.verified_clean


def test_clean_text_untouched():
    text = "The project is 82% complete."
    result = Sanitizer().sanitize(text, [], PolicyAction.SANITIZE)
    assert result.sanitized_text == text


def test_final_verification_catches_residue():
    sanitizer = Sanitizer()
    # Simulate a failed sanitization: secret still present.
    result = sanitizer.verify("token: Bearer abcdefghijklmnop1234567890")
    assert not result.verified_clean
    assert result.remaining_detections


def test_overlapping_spans_merged():
    text = "API key: sk-example-secret-000111222333"
    detected = ApiKeyDetector().detect(text)  # two patterns may both match
    result = Sanitizer().sanitize(text, detected.spans, PolicyAction.REDACT)
    assert result.sanitized_text.count("REDACTED") == 1
