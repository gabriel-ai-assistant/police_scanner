-- Migration: Add audio quality metrics tracking to bcfy_calls_raw
-- Purpose: Track quality scores, processing tiers, SNR, and conversion times
-- for enhanced audio processing pipeline monitoring

-- Add quality metrics columns to bcfy_calls_raw
ALTER TABLE bcfy_calls_raw
  ADD COLUMN IF NOT EXISTS audio_quality_score INTEGER,
  ADD COLUMN IF NOT EXISTS audio_processing_tier TEXT,
  ADD COLUMN IF NOT EXISTS audio_snr_db NUMERIC(5, 2),
  ADD COLUMN IF NOT EXISTS audio_conversion_time_ms INTEGER;

-- Add comments to document the new columns
COMMENT ON COLUMN bcfy_calls_raw.audio_quality_score IS 'Audio quality score (0-100): calculated from SNR estimate. Tier 1 (clean) >70, Tier 2 (moderate) 40-70, Tier 3 (poor) <40';
COMMENT ON COLUMN bcfy_calls_raw.audio_processing_tier IS 'Processing tier applied: TIER1-CLEAN, TIER2-MODERATE, or TIER3-POOR';
COMMENT ON COLUMN bcfy_calls_raw.audio_snr_db IS 'Estimated Signal-to-Noise Ratio in dB, calculated during audio analysis';
COMMENT ON COLUMN bcfy_calls_raw.audio_conversion_time_ms IS 'Time taken to convert MP3 to WAV in milliseconds';

-- Create index for quality analysis queries
CREATE INDEX IF NOT EXISTS idx_calls_quality_score
  ON bcfy_calls_raw(audio_quality_score, processed)
  WHERE processed = TRUE;

CREATE INDEX IF NOT EXISTS idx_calls_processing_tier
  ON bcfy_calls_raw(audio_processing_tier, started_at DESC)
  WHERE audio_processing_tier IS NOT NULL;

-- Create index for conversion time analysis
CREATE INDEX IF NOT EXISTS idx_calls_conversion_time
  ON bcfy_calls_raw(audio_conversion_time_ms, started_at DESC)
  WHERE audio_conversion_time_ms IS NOT NULL;

-- View: Audio quality distribution (last 24 hours)
CREATE OR REPLACE VIEW v_audio_quality_distribution_24h AS
SELECT
  CASE
    WHEN audio_quality_score > 70 THEN 'Tier 1 (Clean)'
    WHEN audio_quality_score > 40 THEN 'Tier 2 (Moderate)'
    WHEN audio_quality_score IS NOT NULL THEN 'Tier 3 (Poor)'
    ELSE 'Unknown'
  END as quality_tier,
  COUNT(*) as call_count,
  ROUND(AVG(audio_quality_score)::numeric, 1) as avg_quality_score,
  ROUND(AVG(audio_snr_db)::numeric, 1) as avg_snr_db,
  ROUND(AVG(audio_conversion_time_ms)::numeric, 0) as avg_conversion_time_ms,
  MIN(audio_quality_score) as min_quality_score,
  MAX(audio_quality_score) as max_quality_score
FROM bcfy_calls_raw
WHERE
  started_at > NOW() - INTERVAL '24 hours'
  AND audio_quality_score IS NOT NULL
GROUP BY quality_tier
ORDER BY avg_quality_score DESC;

-- View: Processing failures by tier
CREATE OR REPLACE VIEW v_audio_processing_failures_by_tier AS
SELECT
  audio_processing_tier as processing_tier,
  error,
  COUNT(*) as failure_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY audio_processing_tier), 1) as failure_percentage
FROM bcfy_calls_raw
WHERE
  error IS NOT NULL
  AND started_at > NOW() - INTERVAL '24 hours'
GROUP BY audio_processing_tier, error
ORDER BY audio_processing_tier, failure_count DESC;

-- View: Conversion performance by time window
CREATE OR REPLACE VIEW v_audio_conversion_performance_hourly AS
SELECT
  DATE_TRUNC('hour', started_at) as hour,
  COUNT(*) as total_calls,
  SUM(CASE WHEN processed = TRUE THEN 1 ELSE 0 END) as successful_conversions,
  SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as failed_conversions,
  ROUND(100.0 * SUM(CASE WHEN processed = TRUE THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as success_rate,
  ROUND(AVG(audio_conversion_time_ms)::numeric, 0) as avg_conversion_time_ms,
  ROUND(AVG(audio_quality_score)::numeric, 1) as avg_quality_score,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY audio_conversion_time_ms) as p95_conversion_time_ms
FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', started_at)
ORDER BY hour DESC;
