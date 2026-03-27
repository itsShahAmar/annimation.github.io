"""
qa_validator.py — Quality control and safety gates for the Food Making Videos Factory.

Provides automated validation checks that run before the upload step:
  1. Duration bounds check
  2. Caption timing overlap check (placeholder — verifies scene count vs duration)
  3. Forbidden term / style blacklist check on script + title
  4. File naming and packaging integrity
  5. Confidence scoring that aggregates all checks into a pass/fail decision

On failure, raises :class:`QAValidationError` with actionable error messages
and optional recovery suggestions.

Key exports
-----------
- :func:`validate_video_output`  — full validation suite on a completed video
- :func:`validate_script`        — script-level text checks
- :func:`validate_metadata`      — title / description / tags checks
- :class:`QAReport`              — structured report dataclass
- :class:`QAValidationError`     — raised on hard failures

Usage::

    from src.qa_validator import validate_video_output, QAReport
    report = validate_video_output(video_path, script_data, audio_duration)
    if not report.passed:
        for issue in report.issues:
            print(issue)
        raise SystemExit(1)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants (overridden by config.py values where relevant)
# ---------------------------------------------------------------------------
_MIN_DURATION_SECONDS: float = 15.0
_MAX_DURATION_SECONDS: float = 60.0
_MIN_CONFIDENCE_SCORE: float = 0.50       # below this → hard fail
_MAX_TITLE_LENGTH: int = 100
_MAX_DESCRIPTION_LENGTH: int = 5000
_MAX_TAGS: int = 500                       # YouTube max total tag characters
_MIN_TAGS: int = 5

# Forbidden content terms for title / script
_FORBIDDEN_SCRIPT_TERMS: list[str] = [
    "explicit", "nsfw", "porn", "xxx", "nude", "naked",
    "kill yourself", "suicide", "self-harm",
    "hate speech", "slur",
]

_FORBIDDEN_TITLE_TERMS: list[str] = [
    "clickbait only", "fake recipe", "poison", "dangerous",
]

# File size bounds
_MIN_VIDEO_SIZE_BYTES: int = 10_000          # 10 KB — catches empty renders
_MAX_VIDEO_SIZE_MB: float = 500.0            # 500 MB


# ---------------------------------------------------------------------------
# Exceptions and data classes
# ---------------------------------------------------------------------------

class QAValidationError(Exception):
    """Raised when a hard QA check fails."""
    def __init__(self, message: str, recovery: str = "") -> None:
        super().__init__(message)
        self.recovery = recovery


@dataclass
class CheckResult:
    """Result of a single QA check."""
    name: str
    passed: bool
    score: float            # 0.0–1.0 contribution to confidence
    message: str
    recovery: str = ""


@dataclass
class QAReport:
    """Aggregated QA validation report."""
    checks: list[CheckResult] = field(default_factory=list)
    confidence_score: float = 0.0       # 0.0–1.0 weighted average
    passed: bool = False
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def format_report(self) -> str:
        """Return a human-readable multi-line QA report."""
        lines = ["=" * 55, "🔍 QA Validation Report", "=" * 55]
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines.append(f"Status          : {status}")
        lines.append(f"Confidence Score: {self.confidence_score:.1%}")
        lines.append("-" * 55)
        for check in self.checks:
            icon = "✅" if check.passed else "❌"
            lines.append(f"  {icon} [{check.score:.2f}] {check.name}: {check.message}")
        if self.issues:
            lines.append("-" * 55)
            lines.append("Issues:")
            for issue in self.issues:
                lines.append(f"  • {issue}")
        if self.suggestions:
            lines.append("Recovery Suggestions:")
            for sug in self.suggestions:
                lines.append(f"  → {sug}")
        lines.append("=" * 55)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_duration(audio_duration: float) -> CheckResult:
    """Validate that the audio/video duration is within acceptable bounds."""
    import config  # noqa: PLC0415
    min_dur = getattr(config, "QA_MIN_DURATION", _MIN_DURATION_SECONDS)
    max_dur = getattr(config, "QA_MAX_DURATION", _MAX_DURATION_SECONDS)

    if audio_duration < min_dur:
        return CheckResult(
            name="duration_bounds",
            passed=False,
            score=0.0,
            message=f"Duration {audio_duration:.1f}s is below minimum {min_dur}s.",
            recovery=f"Increase script word count or reduce TTS pace to reach {min_dur}s+.",
        )
    if audio_duration > max_dur:
        return CheckResult(
            name="duration_bounds",
            passed=False,
            score=0.5,  # soft fail — clipping may still work
            message=f"Duration {audio_duration:.1f}s exceeds maximum {max_dur}s.",
            recovery=f"Trim script to fit within {max_dur}s for YouTube Shorts compliance.",
        )
    return CheckResult(
        name="duration_bounds",
        passed=True,
        score=1.0,
        message=f"Duration {audio_duration:.1f}s is within [{min_dur}s, {max_dur}s].",
    )


def _check_file_integrity(video_path: Path | None) -> CheckResult:
    """Check that the output video file exists and has reasonable size."""
    if video_path is None:
        return CheckResult(
            name="file_integrity",
            passed=False,
            score=0.0,
            message="Video path is None — file was not created.",
            recovery="Check video_creator logs for render errors.",
        )
    if not video_path.exists():
        return CheckResult(
            name="file_integrity",
            passed=False,
            score=0.0,
            message=f"Video file not found at '{video_path}'.",
            recovery="Check video_creator logs; ensure ffmpeg is installed.",
        )
    size_bytes = video_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes < _MIN_VIDEO_SIZE_BYTES:
        return CheckResult(
            name="file_integrity",
            passed=False,
            score=0.0,
            message=f"Video file is suspiciously small ({size_bytes} bytes).",
            recovery="Video may be corrupt — check render logs.",
        )
    if size_mb > _MAX_VIDEO_SIZE_MB:
        return CheckResult(
            name="file_integrity",
            passed=False,
            score=0.5,
            message=f"Video file is very large ({size_mb:.1f} MB > {_MAX_VIDEO_SIZE_MB} MB).",
            recovery="Lower VIDEO_BITRATE in config.py or check for render loop bugs.",
        )
    return CheckResult(
        name="file_integrity",
        passed=True,
        score=1.0,
        message=f"Video file OK ({size_mb:.1f} MB).",
    )


def _check_forbidden_script_terms(script_text: str) -> CheckResult:
    """Scan script text for forbidden / harmful terms."""
    lower = script_text.lower()
    found = [term for term in _FORBIDDEN_SCRIPT_TERMS if term in lower]
    if found:
        return CheckResult(
            name="forbidden_script_terms",
            passed=False,
            score=0.0,
            message=f"Forbidden term(s) in script: {found}",
            recovery="Remove or rephrase the offending content before uploading.",
        )
    return CheckResult(
        name="forbidden_script_terms",
        passed=True,
        score=1.0,
        message="No forbidden terms found in script.",
    )


def _check_forbidden_title_terms(title: str) -> CheckResult:
    """Scan title for forbidden / harmful terms."""
    lower = title.lower()
    found = [term for term in _FORBIDDEN_TITLE_TERMS if term in lower]
    if found:
        return CheckResult(
            name="forbidden_title_terms",
            passed=False,
            score=0.0,
            message=f"Forbidden term(s) in title: {found}",
            recovery="Revise the title to remove the flagged term.",
        )
    return CheckResult(
        name="forbidden_title_terms",
        passed=True,
        score=1.0,
        message="No forbidden terms found in title.",
    )


def _check_title_length(title: str) -> CheckResult:
    """Validate title length within YouTube constraints."""
    if not title or not title.strip():
        return CheckResult(
            name="title_length",
            passed=False,
            score=0.0,
            message="Title is empty.",
            recovery="Ensure scriptwriter returns a non-empty title.",
        )
    length = len(title)
    if length > _MAX_TITLE_LENGTH:
        return CheckResult(
            name="title_length",
            passed=False,
            score=0.5,
            message=f"Title too long ({length} chars > {_MAX_TITLE_LENGTH}).",
            recovery="Shorten the title to 100 characters max for YouTube.",
        )
    return CheckResult(
        name="title_length",
        passed=True,
        score=1.0,
        message=f"Title length OK ({length} chars).",
    )


def _check_tags(tags: list[str]) -> CheckResult:
    """Validate tag count and total character length."""
    if not tags:
        return CheckResult(
            name="tags_completeness",
            passed=False,
            score=0.0,
            message="No tags provided.",
            recovery="Ensure viral_tags_generator returns at least 5 tags.",
        )
    total_chars = sum(len(t) for t in tags)
    if len(tags) < _MIN_TAGS:
        return CheckResult(
            name="tags_completeness",
            passed=False,
            score=0.4,
            message=f"Only {len(tags)} tags provided (minimum {_MIN_TAGS}).",
            recovery="Increase VIRAL_TAGS_TARGET_COUNT in config.py.",
        )
    if total_chars > _MAX_TAGS:
        return CheckResult(
            name="tags_completeness",
            passed=False,
            score=0.6,
            message=f"Total tag characters {total_chars} exceed YouTube max {_MAX_TAGS}.",
            recovery="Reduce tag count or shorten individual tags.",
        )
    return CheckResult(
        name="tags_completeness",
        passed=True,
        score=1.0,
        message=f"Tags OK — {len(tags)} tags, {total_chars} total chars.",
    )


def _check_script_word_count(script_text: str) -> CheckResult:
    """Check that the script has enough words for meaningful narration."""
    words = len(script_text.split())
    if words < 30:
        return CheckResult(
            name="script_word_count",
            passed=False,
            score=0.0,
            message=f"Script too short ({words} words < 30).",
            recovery="Regenerate script — template fallback may have failed.",
        )
    if words > 300:
        return CheckResult(
            name="script_word_count",
            passed=False,
            score=0.6,
            message=f"Script very long ({words} words > 300) — TTS may exceed duration limit.",
            recovery="Consider trimming the script to 150–220 words.",
        )
    return CheckResult(
        name="script_word_count",
        passed=True,
        score=1.0,
        message=f"Script word count OK ({words} words).",
    )


def _check_scene_count(scenes: list[str], audio_duration: float) -> CheckResult:
    """Validate that scene count is appropriate for the audio duration."""
    n = len(scenes)
    if n == 0:
        return CheckResult(
            name="scene_count",
            passed=False,
            score=0.0,
            message="No scenes provided — video will have no visual variety.",
            recovery="Ensure scriptwriter returns at least 3 scene descriptions.",
        )
    # Heuristic: roughly 1 scene per 5–15 seconds is ideal
    min_scenes = max(1, int(audio_duration / 15))
    if n < min_scenes:
        return CheckResult(
            name="scene_count",
            passed=False,
            score=0.5,
            message=f"Only {n} scenes for {audio_duration:.0f}s video (minimum {min_scenes} recommended).",
            recovery="Increase scene count in scriptwriter templates.",
        )
    return CheckResult(
        name="scene_count",
        passed=True,
        score=1.0,
        message=f"Scene count OK ({n} scenes for {audio_duration:.0f}s).",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_script(script_data: dict[str, Any]) -> QAReport:
    """Run script-level QA checks only.

    Args:
        script_data: Dict with keys ``title``, ``script``, ``tags``,
                     ``description``, ``scenes``.

    Returns:
        :class:`QAReport` — always returned (never raises).
    """
    checks: list[CheckResult] = []
    title = script_data.get("title", "")
    script_text = script_data.get("script", "")
    tags = script_data.get("tags", [])

    checks.append(_check_title_length(title))
    checks.append(_check_forbidden_title_terms(title))
    checks.append(_check_forbidden_script_terms(script_text))
    checks.append(_check_script_word_count(script_text))
    checks.append(_check_tags(tags))

    return _build_report(checks)


def validate_metadata(
    title: str,
    description: str,
    tags: list[str],
) -> QAReport:
    """Run metadata-level QA checks (title, description, tags).

    Args:
        title:       Video title string.
        description: Video description string.
        tags:        List of tag strings.

    Returns:
        :class:`QAReport` — always returned (never raises).
    """
    checks: list[CheckResult] = []
    checks.append(_check_title_length(title))
    checks.append(_check_forbidden_title_terms(title))
    checks.append(_check_tags(tags))

    if len(description) > _MAX_DESCRIPTION_LENGTH:
        checks.append(CheckResult(
            name="description_length",
            passed=False,
            score=0.5,
            message=f"Description too long ({len(description)} chars > {_MAX_DESCRIPTION_LENGTH}).",
            recovery="Trim description to fit YouTube's limit.",
        ))
    else:
        checks.append(CheckResult(
            name="description_length",
            passed=True,
            score=1.0,
            message=f"Description length OK ({len(description)} chars).",
        ))

    return _build_report(checks)


def validate_video_output(
    video_path: Path | None,
    script_data: dict[str, Any],
    audio_duration: float,
    hard_fail: bool = False,
) -> QAReport:
    """Run the full QA validation suite on a completed video output.

    Args:
        video_path:      Path to the rendered video file (or None).
        script_data:     Script data dict from the scriptwriter.
        audio_duration:  TTS audio duration in seconds.
        hard_fail:       If True, raises :class:`QAValidationError` on failure.

    Returns:
        :class:`QAReport` with full check results.

    Raises:
        :class:`QAValidationError`: If *hard_fail* is True and report fails.
    """
    title = script_data.get("title", "")
    script_text = script_data.get("script", "")
    tags = script_data.get("tags", [])
    scenes = script_data.get("scenes", [])

    checks: list[CheckResult] = [
        _check_duration(audio_duration),
        _check_file_integrity(video_path),
        _check_forbidden_script_terms(script_text),
        _check_forbidden_title_terms(title),
        _check_title_length(title),
        _check_tags(tags),
        _check_script_word_count(script_text),
        _check_scene_count(scenes, audio_duration),
    ]

    report = _build_report(checks)
    logger.info("\n%s", report.format_report())

    if hard_fail and not report.passed:
        failed = [c for c in checks if not c.passed]
        messages = "; ".join(c.message for c in failed)
        recoveries = "; ".join(c.recovery for c in failed if c.recovery)
        raise QAValidationError(
            f"QA validation failed ({len(failed)} checks): {messages}",
            recovery=recoveries,
        )

    return report


def _build_report(checks: list[CheckResult]) -> QAReport:
    """Aggregate check results into a :class:`QAReport`.

    Args:
        checks: List of individual :class:`CheckResult` objects.

    Returns:
        :class:`QAReport` with confidence score and pass/fail status.
    """
    import config  # noqa: PLC0415
    min_conf = getattr(config, "QA_MIN_CONFIDENCE", _MIN_CONFIDENCE_SCORE)

    if not checks:
        return QAReport(checks=[], confidence_score=1.0, passed=True)

    total_score = sum(c.score for c in checks)
    confidence = total_score / len(checks)

    issues = [f"{c.name}: {c.message}" for c in checks if not c.passed]
    suggestions = [c.recovery for c in checks if not c.passed and c.recovery]

    # Fail if any individual check did not pass OR confidence is too low
    any_failures = [c for c in checks if not c.passed]
    passed = (not any_failures) and (confidence >= min_conf)

    return QAReport(
        checks=checks,
        confidence_score=round(confidence, 4),
        passed=passed,
        issues=issues,
        suggestions=suggestions,
    )
