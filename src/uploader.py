"""
uploader.py — Upload videos to YouTube via the Data API v3.

Credentials are loaded from environment variables (JSON strings) so that
no OAuth2 files need to exist on disk in CI.
"""

import json
import logging
import time
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB resumable upload chunks

# OAuth error codes that indicate a permanent credential problem.  Retrying
# with the same credentials will never succeed — the user must re-authorise.
_FATAL_OAUTH_ERRORS = frozenset({"invalid_scope", "invalid_grant", "invalid_client"})

_REAUTH_HINT = (
    "Your YouTube OAuth2 credentials are invalid or expired.  To fix this:\n"
    "  1. Re-run the OAuth2 authorization flow (see README - Quick Start).\n"
    "  2. Update the YOUTUBE_TOKEN GitHub Secret with the new token JSON.\n"
    "  3. Re-run the pipeline."
)


def _is_fatal_oauth_error(exc: Exception) -> bool:
    """Return ``True`` if *exc* is a credential error that will never succeed on retry."""
    msg = str(exc).lower()
    return any(code in msg for code in _FATAL_OAUTH_ERRORS)


def _build_credentials() -> "google.oauth2.credentials.Credentials":  # type: ignore[name-defined]
    """Build OAuth2 credentials from the environment variable JSON strings.

    Raises:
        RuntimeError: If the required environment variables are missing or
            contain invalid JSON.
    """
    try:
        from google.oauth2.credentials import Credentials  # type: ignore[import]
        from google.auth.transport.requests import Request  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("google-auth package is not installed") from exc

    client_secret_raw = config.YOUTUBE_CLIENT_SECRET_JSON
    token_raw = config.YOUTUBE_TOKEN_JSON

    if not client_secret_raw:
        raise RuntimeError("YOUTUBE_CLIENT_SECRET environment variable is not set")
    if not token_raw:
        raise RuntimeError("YOUTUBE_TOKEN environment variable is not set")

    try:
        client_info = json.loads(client_secret_raw)
        app_info = client_info.get("installed") or client_info.get("web") or client_info
        client_id = app_info["client_id"]
        client_secret = app_info["client_secret"]
        token_uri = app_info.get("token_uri", "https://oauth2.googleapis.com/token")
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid YOUTUBE_CLIENT_SECRET JSON: {exc}") from exc

    try:
        token_info = json.loads(token_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid YOUTUBE_TOKEN JSON: {exc}") from exc

    creds = Credentials(
        token=token_info.get("access_token") or token_info.get("token"),
        refresh_token=token_info.get("refresh_token"),
        client_id=client_id,
        client_secret=client_secret,
        token_uri=token_uri,
    )

    if not creds.refresh_token:
        raise RuntimeError(
            "YOUTUBE_TOKEN contains no refresh_token — the stored credential "
            "is incomplete.\n" + _REAUTH_HINT
        )

    try:
        creds.refresh(Request())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"OAuth2 token refresh failed: {exc}\n{_REAUTH_HINT}"
        ) from exc

    creds._scopes = None           # type: ignore[attr-defined]
    creds._granted_scopes = None   # type: ignore[attr-defined]
    logger.info("OAuth2 token refreshed successfully")

    return creds


def validate_credentials() -> None:
    """Validate that the YouTube OAuth2 credentials are working.

    Builds credentials, refreshes the token, then makes a cheap API call
    (``channels.list mine=True``) to confirm authentication is working.

    Raises:
        RuntimeError: If credentials are missing, invalid, or the API call fails.
    """
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("google-api-python-client is not installed") from exc

    creds = _build_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    try:
        response = youtube.channels().list(part="id", mine=True).execute()
        items = response.get("items", [])
        if items:
            logger.info("Credentials valid — authenticated as channel: %s", items[0]["id"])
        else:
            logger.warning(
                "Credentials valid but no channels found — ensure the OAuth "
                "token was authorized by a YouTube channel owner account."
            )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"YouTube API credential check failed: {exc}\n{_REAUTH_HINT}"
        ) from exc


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = config.YOUTUBE_CATEGORY_ID,
    privacy_status: str = config.PRIVACY_STATUS,
    thumbnail_path: Path | None = None,
) -> tuple[str, str]:
    """Upload a video to YouTube and optionally set its thumbnail.

    Args:
        video_path: Path to the MP4 video file.
        title: Video title (max 100 characters).
        description: Video description.
        tags: List of tag strings.
        category_id: YouTube category ID string (default: ``"22"`` = People & Blogs).
        privacy_status: ``"public"``, ``"unlisted"``, or ``"private"``.
        thumbnail_path: Optional path to a JPEG thumbnail file.

    Returns:
        A tuple of ``(video_id, video_url)``.

    Raises:
        RuntimeError: If the upload fails after all retries.
    """
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
        from googleapiclient.http import MediaFileUpload  # type: ignore[import]
        from googleapiclient.errors import HttpError  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("google-api-python-client is not installed") from exc

    creds = _build_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=_CHUNK_SIZE)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info("Uploading video (attempt %d/%d): '%s'", attempt, _MAX_RETRIES, title)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.debug("Upload progress: %.0f%%", status.progress() * 100)

            video_id: str = response["id"]
            video_url = f"https://www.youtube.com/shorts/{video_id}"
            logger.info("Video uploaded successfully: %s", video_url)

            if thumbnail_path and thumbnail_path.exists():
                _set_thumbnail(youtube, video_id, thumbnail_path)

            return video_id, video_url

        except Exception as exc:  # noqa: BLE001
            logger.warning("Upload attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
            if _is_fatal_oauth_error(exc):
                raise RuntimeError(
                    f"Upload failed due to a permanent credential error: {exc}\n"
                    f"{_REAUTH_HINT}"
                ) from exc
            if attempt < _MAX_RETRIES:
                time.sleep(2**attempt)

    raise RuntimeError(f"Video upload failed after {_MAX_RETRIES} attempts: '{title}'")


def _set_thumbnail(youtube: object, video_id: str, thumbnail_path: Path) -> None:
    """Attach *thumbnail_path* to the already-uploaded *video_id*."""
    try:
        from googleapiclient.discovery import build  # type: ignore[import]
        from googleapiclient.http import MediaFileUpload  # type: ignore[import]
        from googleapiclient.errors import HttpError  # type: ignore[import]
    except ImportError:
        logger.warning("google-api-python-client not available; skipping thumbnail")
        return

    _THUMBNAIL_RETRY_DELAYS = [10, 30, 60]

    for attempt, delay in enumerate(_THUMBNAIL_RETRY_DELAYS, start=1):
        try:
            logger.info("Waiting %d s before setting thumbnail (attempt %d/%d)…",
                        delay, attempt, len(_THUMBNAIL_RETRY_DELAYS))
            time.sleep(delay)

            fresh_creds = _build_credentials()
            fresh_youtube = build("youtube", "v3", credentials=fresh_creds,
                                  cache_discovery=False)

            fresh_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
            fresh_youtube.thumbnails().set(
                videoId=video_id, media_body=fresh_media
            ).execute()
            logger.info("Thumbnail set for video %s", video_id)
            return
        except HttpError as exc:
            status = exc.resp.status if hasattr(exc, "resp") else "unknown"
            logger.warning(
                "Thumbnail attempt %d/%d failed (HTTP %s): %s. "
                "If 403, ensure the channel has custom thumbnails enabled "
                "(requires phone verification) and the OAuth token includes "
                "the youtube.force-ssl scope.",
                attempt, len(_THUMBNAIL_RETRY_DELAYS), status, exc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Thumbnail attempt %d/%d failed: %s",
                           attempt, len(_THUMBNAIL_RETRY_DELAYS), exc)

    logger.warning(
        "Failed to set thumbnail for video %s after %d attempts. "
        "The video was uploaded successfully — thumbnail can be set manually.",
        video_id, len(_THUMBNAIL_RETRY_DELAYS),
    )
