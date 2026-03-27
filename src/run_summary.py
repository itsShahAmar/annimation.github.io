"""
run_summary.py — Structured run summaries, metrics hooks, and audit logs.

Produces a machine-readable JSON audit log entry and a human-readable
run summary at the end of every pipeline execution.  Designed for
easy integration with future dashboarding and alerting systems.

Key exports
-----------
- :class:`RunSummary`       — dataclass capturing all run outcomes
- :func:`start_run`         — create a new :class:`RunSummary` at run start
- :func:`finish_run`        — finalise timing, status, and emit log
- :func:`save_audit_log`    — persist the summary as a JSON artifact
- :func:`format_run_report` — human-readable multi-line summary string

Usage::

    from src.run_summary import start_run, finish_run, save_audit_log
    summary = start_run()
    # ... pipeline steps ...
    finish_run(summary, status="success", topic=topic, title=title, ...)
    save_audit_log(summary, output_dir="artifacts")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class RunSummary:
    """Captures all key outcomes of a single pipeline run.

    Attributes:
        run_id:             ISO-8601 timestamp used as unique run identifier.
        start_time:         Unix epoch seconds when run started.
        end_time:           Unix epoch seconds when run finished (0 = in-progress).
        status:             ``"success"``, ``"failed"``, or ``"dry_run"``.
        topic:              Selected topic (empty if failed before selection).
        title:              Generated video title (empty if failed before).
        style_pack:         Style pack name used for this run.
        cta_strategy:       CTA strategy type used.
        cta_variant:        A/B variant (``"A"`` or ``"B"``).
        trend_score:        Raw trend score of the selected topic.
        virality_score:     Overall virality percentage (0–100).
        qa_confidence:      QA confidence score (0–1).
        qa_passed:          Whether QA gates passed.
        template_used:      Name of script template/source (``"ai"``, ``"template"``).
        music_source:       Music source used (e.g. ``"pixabay"``).
        video_path:         Output video file path (empty if failed).
        upload_url:         YouTube URL (empty if not uploaded).
        upload_id:          YouTube video ID.
        elapsed_seconds:    Total elapsed time in seconds.
        stage_timings:      Dict of stage name → elapsed seconds.
        errors:             List of error strings encountered.
        warnings:           List of warning strings.
        metadata:           Arbitrary extra metadata dict.
    """
    run_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "in_progress"
    topic: str = ""
    title: str = ""
    style_pack: str = ""
    cta_strategy: str = ""
    cta_variant: str = ""
    trend_score: float = 0.0
    virality_score: float = 0.0
    qa_confidence: float = 0.0
    qa_passed: bool = False
    template_used: str = ""
    music_source: str = ""
    video_path: str = ""
    upload_url: str = ""
    upload_id: str = ""
    elapsed_seconds: float = 0.0
    stage_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_stage(self, stage_name: str, elapsed: float) -> None:
        """Record timing for a pipeline stage."""
        self.stage_timings[stage_name] = round(elapsed, 2)

    def add_error(self, msg: str) -> None:
        """Append an error message."""
        self.errors.append(str(msg))
        logger.error("[RunSummary] %s", msg)

    def add_warning(self, msg: str) -> None:
        """Append a warning message."""
        self.warnings.append(str(msg))
        logger.warning("[RunSummary] %s", msg)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_run() -> RunSummary:
    """Create and return a new :class:`RunSummary` with start time set.

    Returns:
        A fresh :class:`RunSummary` in ``"in_progress"`` status.
    """
    now = time.time()
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    summary = RunSummary(run_id=run_id, start_time=now, status="in_progress")
    logger.info("[RunSummary] Run %s started", run_id)
    return summary


def finish_run(
    summary: RunSummary,
    status: str = "success",
    topic: str = "",
    title: str = "",
    style_pack: str = "",
    cta_strategy: str = "",
    cta_variant: str = "",
    trend_score: float = 0.0,
    virality_score: float = 0.0,
    qa_confidence: float = 0.0,
    qa_passed: bool = False,
    template_used: str = "",
    music_source: str = "",
    video_path: str = "",
    upload_url: str = "",
    upload_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> RunSummary:
    """Finalise the :class:`RunSummary` and emit a structured log entry.

    Args:
        summary:        The :class:`RunSummary` started with :func:`start_run`.
        status:         Final status — ``"success"``, ``"failed"``, ``"dry_run"``.
        topic:          Selected topic string.
        title:          Generated video title.
        style_pack:     Style pack name.
        cta_strategy:   CTA strategy type.
        cta_variant:    A/B variant.
        trend_score:    Trend score of selected topic.
        virality_score: Virality percentage.
        qa_confidence:  QA confidence score.
        qa_passed:      Whether QA gates passed.
        template_used:  Script template source.
        music_source:   Music source identifier.
        video_path:     Path to output video file.
        upload_url:     YouTube video URL.
        upload_id:      YouTube video ID.
        metadata:       Additional metadata dict.

    Returns:
        The updated :class:`RunSummary`.
    """
    summary.end_time = time.time()
    summary.elapsed_seconds = round(summary.end_time - summary.start_time, 2)
    summary.status = status
    summary.topic = topic
    summary.title = title
    summary.style_pack = style_pack
    summary.cta_strategy = cta_strategy
    summary.cta_variant = cta_variant
    summary.trend_score = trend_score
    summary.virality_score = virality_score
    summary.qa_confidence = qa_confidence
    summary.qa_passed = qa_passed
    summary.template_used = template_used
    summary.music_source = music_source
    summary.video_path = str(video_path) if video_path else ""
    summary.upload_url = upload_url
    summary.upload_id = upload_id
    if metadata:
        summary.metadata.update(metadata)

    report = format_run_report(summary)
    logger.info("\n%s", report)
    return summary


def format_run_report(summary: RunSummary) -> str:
    """Return a human-readable multi-line run summary.

    Args:
        summary: The :class:`RunSummary` to format.

    Returns:
        Multi-line string report.
    """
    icon = "✅" if summary.status == "success" else ("⚡" if summary.status == "dry_run" else "❌")
    lines = [
        "=" * 60,
        f"{icon} Run Summary [{summary.run_id}]",
        "=" * 60,
        f"  Status         : {summary.status.upper()}",
        f"  Elapsed        : {summary.elapsed_seconds:.1f}s",
        f"  Topic          : {summary.topic or '—'}",
        f"  Title          : {summary.title or '—'}",
        f"  Style Pack     : {summary.style_pack or '—'}",
        f"  CTA Strategy   : {summary.cta_strategy or '—'} (variant {summary.cta_variant or '—'})",
        f"  Trend Score    : {summary.trend_score:.4f}",
        f"  Virality Score : {summary.virality_score:.1f}%",
        f"  QA Confidence  : {summary.qa_confidence:.1%} ({'PASS' if summary.qa_passed else 'FAIL'})",
        f"  Template       : {summary.template_used or '—'}",
        f"  Music Source   : {summary.music_source or '—'}",
        f"  Video Path     : {summary.video_path or '—'}",
        f"  Upload URL     : {summary.upload_url or '—'}",
    ]
    if summary.stage_timings:
        lines.append("  Stage Timings  :")
        for stage, t in summary.stage_timings.items():
            lines.append(f"    {stage:<25}: {t:.1f}s")
    if summary.warnings:
        lines.append(f"  Warnings ({len(summary.warnings)}):")
        for w in summary.warnings:
            lines.append(f"    ⚠ {w}")
    if summary.errors:
        lines.append(f"  Errors ({len(summary.errors)}):")
        for e in summary.errors:
            lines.append(f"    ✘ {e}")
    lines.append("=" * 60)
    return "\n".join(lines)


def save_audit_log(
    summary: RunSummary,
    output_dir: str | Path = "artifacts",
) -> Path:
    """Persist the :class:`RunSummary` as a JSON audit log artifact.

    Creates the output directory if it does not exist.  The filename is
    ``audit_<run_id>.json``.

    Args:
        summary:    The :class:`RunSummary` to persist.
        output_dir: Directory for audit log files.

    Returns:
        Path to the written audit log file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"audit_{summary.run_id}.json"
    log_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    logger.info("Audit log saved to '%s'", log_path)
    return log_path


class _StageTimer:
    """Context manager for timing a named pipeline stage."""

    def __init__(self, summary: RunSummary, stage_name: str) -> None:
        self._summary = summary
        self._stage_name = stage_name
        self._start: float = 0.0

    def __enter__(self) -> "_StageTimer":
        self._start = time.time()
        return self

    def __exit__(self, *_: Any) -> None:
        elapsed = time.time() - self._start
        self._summary.record_stage(self._stage_name, elapsed)


def stage_timer(summary: RunSummary, stage_name: str) -> _StageTimer:
    """Return a context manager that times a pipeline stage.

    Example::

        with stage_timer(summary, "tts"):
            audio_path, duration = generate_speech(script_text)

    Args:
        summary:    The active :class:`RunSummary`.
        stage_name: Short identifier for the stage.

    Returns:
        :class:`_StageTimer` context manager.
    """
    return _StageTimer(summary, stage_name)
