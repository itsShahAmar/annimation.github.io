"""
tests/test_uploader.py — Unit tests for src/uploader.py

All tests mock the Google API client so no real network calls are made.
Run with: python -m pytest tests/ -v
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Stub out heavy optional imports so tests run without installing everything
# ---------------------------------------------------------------------------
_google_stub = MagicMock()
sys.modules.setdefault("google", _google_stub)
sys.modules.setdefault("google.oauth2", _google_stub)
sys.modules.setdefault("google.oauth2.credentials", _google_stub)
sys.modules.setdefault("google.auth", _google_stub)
sys.modules.setdefault("google.auth.transport", _google_stub)
sys.modules.setdefault("google.auth.transport.requests", _google_stub)
sys.modules.setdefault("googleapiclient", _google_stub)
sys.modules.setdefault("googleapiclient.discovery", _google_stub)
sys.modules.setdefault("googleapiclient.http", _google_stub)
sys.modules.setdefault("googleapiclient.errors", _google_stub)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CLIENT_SECRET = json.dumps({
    "installed": {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
})

_VALID_TOKEN = json.dumps({
    "access_token": "ya29.test-access-token",
    "refresh_token": "1//test-refresh-token",
    "token_uri": "https://oauth2.googleapis.com/token",
})

_TOKEN_NO_REFRESH = json.dumps({
    "access_token": "ya29.test-access-token",
    "token_uri": "https://oauth2.googleapis.com/token",
})


class TestBuildCredentials(unittest.TestCase):
    """Tests for _build_credentials()."""

    def _make_mock_creds(self, refresh_token="1//test-refresh-token"):
        creds = MagicMock()
        creds.refresh_token = refresh_token
        creds._scopes = None
        creds._granted_scopes = None
        return creds

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_raises_when_google_auth_not_installed(self):
        """ImportError from google.oauth2 should surface as RuntimeError."""
        import src.uploader as uploader

        with patch.dict(sys.modules, {
            "google.oauth2.credentials": None,
            "google.auth.transport.requests": None,
        }):
            self.assertTrue(callable(uploader._build_credentials))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", None)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_raises_when_client_secret_missing(self):
        import src.uploader as uploader
        with self.assertRaises(RuntimeError) as ctx:
            uploader._build_credentials()
        self.assertIn("YOUTUBE_CLIENT_SECRET", str(ctx.exception))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", None)
    def test_raises_when_token_missing(self):
        import src.uploader as uploader
        with self.assertRaises(RuntimeError) as ctx:
            uploader._build_credentials()
        self.assertIn("YOUTUBE_TOKEN", str(ctx.exception))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", "not-valid-json{{{")
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_raises_on_invalid_client_secret_json(self):
        import src.uploader as uploader
        with self.assertRaises(RuntimeError) as ctx:
            uploader._build_credentials()
        self.assertIn("YOUTUBE_CLIENT_SECRET", str(ctx.exception))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", "bad-json")
    def test_raises_on_invalid_token_json(self):
        import src.uploader as uploader
        with self.assertRaises(RuntimeError) as ctx:
            uploader._build_credentials()
        self.assertIn("YOUTUBE_TOKEN", str(ctx.exception))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _TOKEN_NO_REFRESH)
    def test_raises_when_refresh_token_missing(self):
        """A token without a refresh_token should raise with a re-auth hint."""
        import src.uploader as uploader

        mock_creds = self._make_mock_creds(refresh_token=None)

        with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"):
            with self.assertRaises(RuntimeError) as ctx:
                uploader._build_credentials()
        self.assertIn("refresh_token", str(ctx.exception))

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_scopes_cleared_after_refresh(self):
        """After refresh, _scopes and _granted_scopes must be None."""
        import src.uploader as uploader

        mock_creds = self._make_mock_creds()

        def fake_refresh(request):
            mock_creds._scopes = frozenset(["https://www.googleapis.com/auth/youtube.upload"])
            mock_creds._granted_scopes = frozenset(["https://www.googleapis.com/auth/youtube.upload"])

        mock_creds.refresh = fake_refresh

        with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"):
            result = uploader._build_credentials()

        self.assertIsNone(result._scopes,
                          "_scopes should be None after _build_credentials()")
        self.assertIsNone(result._granted_scopes,
                          "_granted_scopes should be None after _build_credentials()")

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_raises_when_refresh_fails(self):
        """Any exception during refresh should raise RuntimeError with re-auth hint."""
        import src.uploader as uploader

        mock_creds = self._make_mock_creds()
        mock_creds.refresh.side_effect = Exception("invalid_grant")

        with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"):
            with self.assertRaises(RuntimeError) as ctx:
                uploader._build_credentials()

        self.assertIn("OAuth2 token refresh failed", str(ctx.exception))
        self.assertIn("YOUTUBE_TOKEN", str(ctx.exception))


class TestIsFatalOAuthError(unittest.TestCase):
    """Tests for _is_fatal_oauth_error()."""

    def setUp(self):
        import src.uploader as uploader
        self.fn = uploader._is_fatal_oauth_error

    def test_invalid_scope_is_fatal(self):
        self.assertTrue(self.fn(Exception("invalid_scope: Bad Request")))

    def test_invalid_grant_is_fatal(self):
        self.assertTrue(self.fn(Exception("invalid_grant")))

    def test_invalid_client_is_fatal(self):
        self.assertTrue(self.fn(Exception("invalid_client")))

    def test_transient_error_is_not_fatal(self):
        self.assertFalse(self.fn(Exception("Connection timed out")))

    def test_http_500_is_not_fatal(self):
        self.assertFalse(self.fn(Exception("HttpError 500")))


class TestValidateCredentials(unittest.TestCase):
    """Tests for validate_credentials()."""

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_passes_when_channel_found(self):
        import src.uploader as uploader

        mock_creds = MagicMock()
        mock_creds.refresh_token = "1//test"
        mock_creds._scopes = None
        mock_creds._granted_scopes = None

        mock_youtube = MagicMock()
        mock_youtube.channels().list().execute.return_value = {
            "items": [{"id": "UCtest123"}]
        }

        with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"), \
             patch("googleapiclient.discovery.build", return_value=mock_youtube):
            uploader.validate_credentials()

    @patch("config.YOUTUBE_CLIENT_SECRET_JSON", _VALID_CLIENT_SECRET)
    @patch("config.YOUTUBE_TOKEN_JSON", _VALID_TOKEN)
    def test_raises_when_api_call_fails(self):
        import src.uploader as uploader

        mock_creds = MagicMock()
        mock_creds.refresh_token = "1//test"
        mock_creds._scopes = None
        mock_creds._granted_scopes = None

        mock_youtube = MagicMock()
        mock_youtube.channels().list().execute.side_effect = Exception("403 forbidden")

        with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
             patch("google.auth.transport.requests.Request"), \
             patch("googleapiclient.discovery.build", return_value=mock_youtube):
            with self.assertRaises(RuntimeError) as ctx:
                uploader.validate_credentials()

        self.assertIn("credential check failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
