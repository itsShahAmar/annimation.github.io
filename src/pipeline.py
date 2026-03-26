"""
pipeline.py — Main orchestrator for the Food Making Videos Factory pipeline.

Runs all steps in sequence:
  0. Validate YouTube credentials (fail fast)
  1. Trend ingestion and scoring (get_best_topic + trend_scorer)
  2. Script and shot-list generation (enhanced_scriptwriter / scriptwriter)
  3. CTA injection and hook generation (cta_engine)
  4. Style pack selection and scene enrichment (style_packs)
  5. TTS narration and background music
  6. Video render and export (video_creator)
  7. QA validation gates (qa_validator)
  8. Virality analysis (virality_optimizer)
  9. Publish to YouTube and save audit log

Usage::

    python -m src.pipeline              # full run
    DRY_RUN=true python -m src.pipeline # skip upload, save artifacts only
"""

import logging
import time
from pathlib import Path

import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _cleanup(*paths: Path | None) -> None:
    """Delete temporary files, ignoring errors."""
    for p in paths:
        if p is not None:
            try:
                p.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass


def run_pipeline() -> None:
    """Execute the full Food Making Videos Factory creation and upload pipeline."""
    from src.run_summary import start_run, finish_run, save_audit_log, stage_timer  # noqa: PLC0415

    summary = start_run()
    dry_run: bool = getattr(config, "DRY_RUN", False)

    logger.info("=" * 60)
    logger.info("\U0001f373 Food Making Videos Factory — pipeline starting (dry_run=%s)", dry_run)
    logger.info("=" * 60)

    audio_path: Path | None = None
    video_path: Path | None = None
    topic: str = ""
    title: str = ""
    script_data: dict = {}
    video_id: str = ""
    video_url: str = ""
    cta_strategy: str = ""
    cta_variant: str = getattr(config, "CTA_AB_VARIANT", "A")
    style_name: str = ""
    template_used: str = ""
    music_source: str = ""
    virality_pct: float = 0.0
    qa_confidence: float = 1.0
    qa_passed: bool = True

    try:
        # ------------------------------------------------------------------
        # Step 0: Validate YouTube credentials (fail fast before heavy work)
        # ------------------------------------------------------------------
        logger.info("[0/9] \U0001f511 Validating credentials…")
        with stage_timer(summary, "credentials"):
            from src.uploader import validate_credentials  # noqa: PLC0415
            if not dry_run:
                validate_credentials()
                logger.info("      Credentials OK")
            else:
                logger.info("      DRY RUN — skipping credential validation")

        # ------------------------------------------------------------------
        # Step 1: Trend ingestion and scoring
        # ------------------------------------------------------------------
        logger.info("[1/9] \U0001f525 Trend ingestion — fetching and scoring trending topics…")
        with stage_timer(summary, "trend_ingestion"):
            from src.trending import get_trending_topics, get_best_topic  # noqa: PLC0415

            if getattr(config, "TREND_SCORER_ENABLED", True):
                from src.trend_scorer import select_best_topic, save_trend_digest, record_used_topic  # noqa: PLC0415

                raw_topics = get_trending_topics()
                history_path = getattr(config, "TREND_HISTORY_PATH", "artifacts/topic_history.json")
                topic, scored_topics = select_best_topic(
                    raw_topics,
                    history_path=history_path,
                    top_k=getattr(config, "TREND_TOP_K", 5),
                )
                selected_scored = next((s for s in scored_topics if s.topic == topic), None)
                if selected_scored:
                    summary.trend_score = selected_scored.raw_score

                if getattr(config, "TREND_DIGEST_ENABLED", True):
                    try:
                        save_trend_digest(scored_topics, topic,
                                          output_dir=getattr(config, "TREND_DIGEST_DIR", "artifacts"))
                    except Exception as exc:  # noqa: BLE001
                        summary.add_warning(f"Trend digest save failed: {exc}")

                record_used_topic(topic, history_path=history_path)
            else:
                topic = get_best_topic()

        logger.info("      Food topic selected: '%s'", topic)
        summary.topic = topic

        # ------------------------------------------------------------------
        # Step 2: Style pack selection
        # ------------------------------------------------------------------
        logger.info("[2/9] \U0001f3a8 Style — selecting cinematic style pack…")
        with stage_timer(summary, "style_selection"):
            style_scenes_override: list[str] | None = None
            style_color_params: dict = {}

            if getattr(config, "STYLE_PACK_ENABLED", True):
                from src.style_packs import select_style_for_topic, get_style_pack  # noqa: PLC0415
                pack_name = getattr(config, "STYLE_PACK_NAME", "auto")
                if pack_name == "auto":
                    style_pack = select_style_for_topic(topic)
                else:
                    style_pack = get_style_pack(pack_name)
                style_name = style_pack.name
                logger.info("      Style pack: '%s' (%s pacing, %s transition)",
                            style_pack.display_name, style_pack.pacing, style_pack.transition_style)
                summary.style_pack = style_name
            else:
                style_pack = None

        # ------------------------------------------------------------------
        # Step 3: Generate professional food script via OpenRouter AI
        # ------------------------------------------------------------------
        logger.info("[3/9] \u270d\ufe0f  Writing — generating AI food script for: '%s'…", topic)
        with stage_timer(summary, "script_generation"):
            prompt_modifiers = ""
            if style_pack is not None:
                from src.style_packs import get_prompt_modifier_string  # noqa: PLC0415
                prompt_modifiers = get_prompt_modifier_string(style_pack)

            if getattr(config, "ENHANCED_SCRIPT_ENABLED", True):
                try:
                    from src.enhanced_scriptwriter import generate_enhanced_script  # noqa: PLC0415
                    script_data = generate_enhanced_script(topic)
                    template_used = "enhanced_ai"
                    logger.info("      Enhanced step-by-step script generated")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Enhanced scriptwriter failed (%s) — using standard scriptwriter", exc)
                    from src.scriptwriter import generate_script  # noqa: PLC0415
                    script_data = generate_script(topic)
                    template_used = "standard_ai"
            else:
                from src.scriptwriter import generate_script  # noqa: PLC0415
                script_data = generate_script(topic)
                template_used = "standard_ai"

            title = script_data["title"]
            script_text = script_data["script"]
            caption_text = script_data["caption_script"]
            hook_text = script_data["hook"]
            scenes = script_data["scenes"]
            tags = script_data["tags"]
            description = script_data["description"]
            summary.title = title
            summary.template_used = template_used
            logger.info("      Food video title: '%s'", title)
            logger.info("      Tags count: %d | Template: %s", len(tags), template_used)

        # ------------------------------------------------------------------
        # Step 4: CTA injection and hook generation
        # ------------------------------------------------------------------
        logger.info("[4/9] \U0001f3af CTA — injecting conversion hooks and subscribe prompts…")
        with stage_timer(summary, "cta_injection"):
            if getattr(config, "CTA_ENGINE_ENABLED", True):
                from src.cta_engine import CTAContext, inject_cta_into_script  # noqa: PLC0415
                cta_ctx = CTAContext(
                    topic=topic,
                    style=getattr(config, "CTA_STRATEGY", "auto"),
                    platform=getattr(config, "CTA_PLATFORM", "youtube_shorts"),
                    ab_variant=cta_variant,
                )
                injected = inject_cta_into_script(script_text, cta_ctx)
                script_text = injected.text
                hook_text = injected.hook
                cta_strategy = injected.strategy_used.value
                script_data["script"] = script_text
                script_data["hook"] = hook_text
                summary.cta_strategy = cta_strategy
                summary.cta_variant = cta_variant
                logger.info("      CTA strategy: %s | variant: %s | hook set",
                            cta_strategy, cta_variant)

        # ------------------------------------------------------------------
        # Step 4.5: Enrich scenes with style pack cues
        # ------------------------------------------------------------------
        if style_pack is not None and getattr(config, "STYLE_PACK_ENRICH_SCENES", True):
            from src.style_packs import build_scene_queries  # noqa: PLC0415
            scenes = build_scene_queries(scenes, style_pack)
            script_data["scenes"] = scenes
            logger.info("      Scene queries enriched with '%s' style cues", style_name)

        # ------------------------------------------------------------------
        # Step 5: Text-to-speech (professional female voice narration)
        # ------------------------------------------------------------------
        logger.info("[5/9] \U0001f3a4 Narrating — generating professional female TTS audio…")
        with stage_timer(summary, "tts"):
            from src.tts import generate_speech  # noqa: PLC0415
            audio_path, audio_duration = generate_speech(script_text)
            logger.info("      Audio duration: %.2f s", audio_duration)

        # ------------------------------------------------------------------
        # Step 5.5: Select scene-aware background music (free sources)
        # ------------------------------------------------------------------
        logger.info("[5.5/9] \U0001f3b5 Music — selecting scene-aware background music…")
        with stage_timer(summary, "music_selection"):
            from src.music_selector import get_music_for_scenes  # noqa: PLC0415
            music_path = get_music_for_scenes(scenes, topic)
            if music_path:
                logger.info("      Background music: '%s'", music_path)
                music_source = music_path.stem if hasattr(music_path, "stem") else str(music_path)
            else:
                logger.info("      No background music — using TTS narration only")
            summary.music_source = music_source or "none"

        # ------------------------------------------------------------------
        # Step 6: Create food-style video
        # ------------------------------------------------------------------
        logger.info("[6/9] \U0001f3ac Assembling — creating cinematic food video…")
        with stage_timer(summary, "video_render"):
            from src.video_creator import create_video  # noqa: PLC0415
            video_path = create_video(audio_path, script_text, scenes, audio_duration,
                                      hook_text=hook_text, music_path=music_path)
            summary.video_path = str(video_path)
            logger.info("      Video path: '%s'", video_path)

        # ------------------------------------------------------------------
        # Step 7: QA validation gates
        # ------------------------------------------------------------------
        if getattr(config, "QA_ENABLED", True):
            logger.info("[7/9] \U0001f50d QA — running validation gates…")
            with stage_timer(summary, "qa_validation"):
                try:
                    from src.qa_validator import validate_video_output  # noqa: PLC0415
                    qa_report = validate_video_output(
                        video_path=video_path,
                        script_data=script_data,
                        audio_duration=audio_duration,
                        hard_fail=getattr(config, "QA_HARD_FAIL", False),
                    )
                    qa_confidence = qa_report.confidence_score
                    qa_passed = qa_report.passed
                    summary.qa_confidence = qa_confidence
                    summary.qa_passed = qa_passed
                    if not qa_passed:
                        for issue in qa_report.issues:
                            summary.add_warning(f"QA: {issue}")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("      QA validation error: %s — continuing", exc)
                    summary.add_warning(f"QA validation exception: {exc}")

        # ------------------------------------------------------------------
        # Step 8: Virality optimization analysis
        # ------------------------------------------------------------------
        if getattr(config, "VIRALITY_OPTIMIZATION_ENABLED", True):
            logger.info("[8/9] \U0001f4ca Optimizing — running virality analysis…")
            with stage_timer(summary, "virality_analysis"):
                try:
                    from src.virality_optimizer import analyze_virality  # noqa: PLC0415
                    vreport = analyze_virality(script_data, topic, music_path=music_path)
                    logger.info("\n%s", vreport.format_report())
                    virality_pct = vreport.overall_percentage
                    summary.virality_score = virality_pct
                    min_score = getattr(config, "VIRALITY_MIN_SCORE", 0.0)
                    if vreport.overall_score < min_score:
                        logger.warning(
                            "      Virality score %.1f%% is below minimum %.1f%% — "
                            "proceeding anyway",
                            vreport.overall_percentage, min_score * 100,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("      Virality optimization failed: %s — continuing", exc)
                    summary.add_warning(f"Virality analysis exception: {exc}")

        # ------------------------------------------------------------------
        # Step 9: Upload to YouTube (or dry-run skip)
        # ------------------------------------------------------------------
        if dry_run:
            logger.info("[9/9] \u26a1 DRY RUN — skipping YouTube upload")
            video_id = "DRY_RUN"
            video_url = "https://example.com/dry-run"
            summary_status = "dry_run"
        else:
            logger.info("[9/9] \U0001f680 Upload and go viral — uploading to YouTube…")
            with stage_timer(summary, "upload"):
                from src.uploader import upload_video  # noqa: PLC0415
                video_id, video_url = upload_video(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                )
                logger.info("      Upload complete: %s", video_url)
            summary_status = "success"

        # ------------------------------------------------------------------
        # Finalise run summary and audit log
        # ------------------------------------------------------------------
        finish_run(
            summary,
            status=summary_status,
            topic=topic,
            title=title,
            style_pack=style_name,
            cta_strategy=cta_strategy,
            cta_variant=cta_variant,
            trend_score=summary.trend_score,
            virality_score=virality_pct,
            qa_confidence=qa_confidence,
            qa_passed=qa_passed,
            template_used=template_used,
            music_source=music_source or "none",
            video_path=str(video_path) if video_path else "",
            upload_url=video_url,
            upload_id=video_id,
        )

        if getattr(config, "AUDIT_LOG_ENABLED", True):
            try:
                save_audit_log(summary, output_dir=getattr(config, "AUDIT_LOG_DIR", "artifacts"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Audit log save failed: %s", exc)

    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - summary.start_time
        logger.error("\U0001f4a5 Pipeline failed after %.1f seconds: %s", elapsed, exc, exc_info=True)
        summary.add_error(str(exc))
        finish_run(summary, status="failed", topic=topic, title=title)
        if getattr(config, "AUDIT_LOG_ENABLED", True):
            try:
                save_audit_log(summary, output_dir=getattr(config, "AUDIT_LOG_DIR", "artifacts"))
            except Exception:  # noqa: BLE001
                pass
    finally:
        _cleanup(audio_path, video_path)
        logger.info("\U0001f9f9 Temporary files cleaned up")


if __name__ == "__main__":
    run_pipeline()
