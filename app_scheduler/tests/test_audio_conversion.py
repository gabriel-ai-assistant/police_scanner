#!/usr/bin/env python3
"""
Test suite for validating audio conversion improvements.

This script tests the enhanced audio processing pipeline by:
1. Testing audio analysis and quality scoring
2. Validating tier selection based on quality
3. Testing FFmpeg command generation
4. Validating output WAV files
5. Measuring performance metrics
6. A/B testing old vs new processing (if both available)
"""

import json
import logging
import os
import sys
import tempfile
import time

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    import librosa  # noqa: F401
except ImportError:
    print("ERROR: librosa is required. Install with: pip install librosa")
    sys.exit(1)

from get_calls import (
    analyze_audio_enhanced,
    build_ffmpeg_command,
    build_tier1_filters,
    build_tier2_filters,
    build_tier3_filters,
    validate_wav_output,
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# Test constants
TEST_RESULTS = {
    'tests_passed': 0,
    'tests_failed': 0,
    'test_details': []
}


def assert_true(condition, test_name, error_msg=""):
    """Helper function for assertions."""
    global TEST_RESULTS
    if condition:
        TEST_RESULTS['tests_passed'] += 1
        log.info(f"✓ {test_name}")
        return True
    else:
        TEST_RESULTS['tests_failed'] += 1
        log.error(f"✗ {test_name}: {error_msg}")
        TEST_RESULTS['test_details'].append({
            'test': test_name,
            'status': 'FAILED',
            'error': error_msg
        })
        return False


def test_audio_analysis():
    """Test enhanced audio analysis function."""
    log.info("\n" + "="*60)
    log.info("TEST SUITE: Audio Analysis")
    log.info("="*60)

    # Create a test sine wave audio file (1 second, 16kHz)
    sr = 16000
    duration = 1.0
    frequency = 1000  # 1 kHz sine wave

    # Create clean audio
    t = np.linspace(0, duration, int(sr * duration))
    clean_audio = 0.5 * np.sin(2 * np.pi * frequency * t)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        clean_path = f.name

    try:
        # Write test audio to WAV
        import soundfile as sf
        sf.write(clean_path, clean_audio, sr)

        # Test analysis
        analysis = analyze_audio_enhanced(clean_path)

        # Validate analysis output
        assert_true(
            'quality_score' in analysis,
            "Audio analysis includes quality_score",
            f"Missing quality_score in {analysis.keys()}"
        )

        assert_true(
            0 <= analysis['quality_score'] <= 100,
            "Quality score is in valid range (0-100)",
            f"Quality score {analysis['quality_score']} out of range"
        )

        assert_true(
            'snr_estimate' in analysis,
            "Audio analysis includes SNR estimate",
            f"Missing snr_estimate in {analysis.keys()}"
        )

        assert_true(
            'rms' in analysis and isinstance(analysis['rms'], (int, float)),
            "RMS value is numeric",
            f"Invalid RMS: {analysis.get('rms')}"
        )

        log.info(f"  Analysis results: {json.dumps({k: v for k, v in analysis.items() if isinstance(v, (int, float))}, indent=2)}")

    finally:
        os.unlink(clean_path)


def test_tier_selection():
    """Test tier selection logic based on quality score."""
    log.info("\n" + "="*60)
    log.info("TEST SUITE: Tier Selection")
    log.info("="*60)

    # Create mock analysis results for different quality levels
    clean_analysis = {'quality_score': 80, 'snr_estimate': 20, 'rms': -15}
    moderate_analysis = {'quality_score': 55, 'snr_estimate': 12, 'rms': -20}
    poor_analysis = {'quality_score': 25, 'snr_estimate': 5, 'rms': -28}

    # Test tier selection
    tier1_filters = build_tier1_filters(clean_analysis)
    tier2_filters = build_tier2_filters(moderate_analysis)
    tier3_filters = build_tier3_filters(poor_analysis)

    assert_true(
        len(tier1_filters) > 0,
        "Tier 1 filter chain is not empty",
        f"Got {len(tier1_filters)} filters"
    )

    assert_true(
        len(tier2_filters) > len(tier1_filters),
        "Tier 2 has more filters than Tier 1",
        f"Tier1: {len(tier1_filters)}, Tier2: {len(tier2_filters)}"
    )

    assert_true(
        len(tier3_filters) > len(tier2_filters),
        "Tier 3 has more filters than Tier 2",
        f"Tier2: {len(tier2_filters)}, Tier3: {len(tier3_filters)}"
    )

    assert_true(
        'speechnorm' in ','.join(tier2_filters),
        "Tier 2 includes speechnorm filter",
        f"Filters: {tier2_filters}"
    )

    assert_true(
        'afwtdn' in ','.join(tier2_filters),
        "Tier 2 includes wavelet denoising",
        f"Filters: {tier2_filters}"
    )

    assert_true(
        'anlmdn' in ','.join(tier3_filters),
        "Tier 3 includes non-local means denoising",
        f"Filters: {tier3_filters}"
    )

    log.info(f"  Tier 1 filters: {len(tier1_filters)}")
    log.info(f"  Tier 2 filters: {len(tier2_filters)}")
    log.info(f"  Tier 3 filters: {len(tier3_filters)}")


def test_ffmpeg_command_building():
    """Test FFmpeg command generation."""
    log.info("\n" + "="*60)
    log.info("TEST SUITE: FFmpeg Command Building")
    log.info("="*60)

    # Create a test WAV file
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 1000 * t)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        input_path = f.name
        output_path = input_path.replace('.wav', '_out.wav')

    try:
        import soundfile as sf
        sf.write(input_path, audio, sr)

        # Test command building
        cmd, analysis = build_ffmpeg_command(input_path, output_path)

        assert_true(
            cmd is not None and len(cmd) > 0,
            "FFmpeg command is generated",
            f"Got command: {cmd}"
        )

        assert_true(
            'ffmpeg' in cmd[0],
            "Command starts with ffmpeg",
            f"First element: {cmd[0]}"
        )

        assert_true(
            '-filter:a' in cmd,
            "Command includes audio filter parameter",
            f"Command: {cmd}"
        )

        assert_true(
            analysis is not None,
            "Audio analysis is returned with command",
            f"Analysis: {analysis}"
        )

        log.info(f"  Generated command: {' '.join(cmd[:5])}...")
        log.info(f"  Filter chain includes {len(cmd[cmd.index('-filter:a') + 1].split(','))} filters")

    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)


def test_output_validation():
    """Test WAV output validation."""
    log.info("\n" + "="*60)
    log.info("TEST SUITE: Output Validation")
    log.info("="*60)

    # Create a valid test WAV
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 1000 * t)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name

    try:
        import soundfile as sf
        sf.write(wav_path, audio, sr)

        # Test validation
        is_valid, msg = validate_wav_output(wav_path, expected_duration_sec=duration)

        assert_true(
            is_valid,
            "Valid WAV passes validation",
            f"Validation failed: {msg}"
        )

        log.info(f"  Validation message: {msg}")

        # Test invalid file
        is_valid_invalid, msg_invalid = validate_wav_output("/nonexistent/file.wav")
        assert_true(
            not is_valid_invalid,
            "Nonexistent file fails validation",
            f"Should have failed but got: {msg_invalid}"
        )

        # Test duration mismatch
        is_valid_duration, msg_duration = validate_wav_output(wav_path, expected_duration_sec=10.0)
        assert_true(
            not is_valid_duration,
            "Duration mismatch is detected",
            f"Should have failed but got: {msg_duration}"
        )

    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def test_performance():
    """Test performance characteristics."""
    log.info("\n" + "="*60)
    log.info("TEST SUITE: Performance")
    log.info("="*60)

    # Create test audio
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    # Create more realistic audio with noise
    audio = 0.5 * np.sin(2 * np.pi * 1000 * t) + 0.1 * np.random.randn(len(t))
    audio = np.clip(audio, -1, 1)  # Prevent clipping

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name

    try:
        import soundfile as sf
        sf.write(wav_path, audio, sr)

        # Time analysis
        start = time.time()
        analyze_audio_enhanced(wav_path)
        analysis_time = time.time() - start

        assert_true(
            analysis_time < 2.0,
            f"Audio analysis completes in < 2 seconds ({analysis_time:.2f}s)",
            f"Analysis took {analysis_time:.2f}s"
        )

        log.info(f"  Analysis time: {analysis_time:.3f}s for {duration}s audio")
        log.info(f"  Performance ratio: {(analysis_time / duration):.2f}x real-time")

    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def print_summary():
    """Print test summary."""
    log.info("\n" + "="*60)
    log.info("TEST SUMMARY")
    log.info("="*60)

    total = TEST_RESULTS['tests_passed'] + TEST_RESULTS['tests_failed']
    passed = TEST_RESULTS['tests_passed']
    failed = TEST_RESULTS['tests_failed']

    log.info(f"Total tests: {total}")
    log.info(f"Passed: {passed} ✓")
    log.info(f"Failed: {failed} ✗")

    if failed > 0:
        log.info("\nFailed tests:")
        for detail in TEST_RESULTS['test_details']:
            log.info(f"  - {detail['test']}: {detail['error']}")

    success_rate = 100 * (passed / total) if total > 0 else 0
    log.info(f"\nSuccess rate: {success_rate:.1f}%")

    return failed == 0


def main():
    """Run all tests."""
    log.info("Starting audio conversion test suite...")

    try:
        test_audio_analysis()
        test_tier_selection()
        test_ffmpeg_command_building()
        test_output_validation()
        test_performance()

        success = print_summary()
        return 0 if success else 1

    except Exception as e:
        log.exception(f"Test suite failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
