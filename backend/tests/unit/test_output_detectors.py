"""Output detector unit tests."""

from asguard.output_guard.detectors import (
    ApiKeyDetector,
    PasswordDetector,
    TokenDetector,
)
from asguard.output_guard.pii_detectors import (
    ConfidentialDetector,
    EmailDetector,
    FinancialDetector,
    PhoneDetector,
)


class TestApiKeyDetector:
    def test_openai_style_key(self):
        result = ApiKeyDetector().detect("Your key is sk-example-secret-000111222333.")
        assert result.detected
        assert result.spans[0].label == "api_key"
        assert "sk-example" not in result.spans[0].masked_preview  # masked

    def test_github_token(self):
        assert ApiKeyDetector().detect("token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456").detected

    def test_labeled_key(self):
        assert ApiKeyDetector().detect("api_key: abcd1234efgh5678").detected

    def test_benign(self):
        assert not ApiKeyDetector().detect("The API gateway key rotation happens monthly.").detected


class TestPasswordDetector:
    def test_password(self):
        assert PasswordDetector().detect("password: SuperSecret123").detected

    def test_private_key_block(self):
        assert PasswordDetector().detect("-----BEGIN RSA PRIVATE KEY-----").detected

    def test_benign(self):
        assert not PasswordDetector().detect("Use a strong password for safety.").detected


class TestTokenDetector:
    def test_bearer(self):
        result = TokenDetector().detect("Bearer abcdefghijklmnop1234567890")
        assert result.detected

    def test_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.dozjgNryP4J3jVmNHl0w"
        assert TokenDetector().detect(f"token: {jwt}").detected


class TestPhoneDetector:
    def test_international(self):
        result = PhoneDetector().detect("Call +212 6 12 34 56 78 now.")
        assert result.detected

    def test_us_number(self):
        assert PhoneDetector().detect("(555) 123-4567").detected

    def test_short_number_not_flagged(self):
        assert not PhoneDetector().detect("Room number 12 34 is available.").detected


class TestEmailDetector:
    def test_email(self):
        result = EmailDetector().detect("Contact admin@example-corp.com today.")
        assert result.detected

    def test_benign(self):
        assert not EmailDetector().detect("No addresses here.").detected


class TestFinancialDetector:
    def test_luhn_valid_card(self):
        assert FinancialDetector().detect("card 4111 1111 1111 1111").detected

    def test_luhn_invalid_not_flagged(self):
        assert not FinancialDetector().detect("order 4111 1111 1111 1112").detected

    def test_salary(self):
        assert FinancialDetector().detect("Her salary is 95,000 EUR").detected

    def test_plain_numbers(self):
        assert not FinancialDetector().detect("The project is 82% complete.").detected


class TestConfidentialDetector:
    def test_confidential_marker(self):
        assert ConfidentialDetector().detect("This is confidential information.").detected

    def test_benign(self):
        assert not ConfidentialDetector().detect("Public announcement: hello world.").detected
