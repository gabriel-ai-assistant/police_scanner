"""
Location Text Extraction from Transcripts.

Extracts addresses, streets, intersections, businesses, and landmarks
from police scanner transcript text.
"""
import re
import logging
from typing import List, Optional, Tuple

from app.models import ExtractedLocation

logger = logging.getLogger(__name__)

# Common street suffixes
STREET_SUFFIXES = r'(?:street|st|avenue|ave|boulevard|blvd|road|rd|drive|dr|lane|ln|court|ct|way|circle|cir|place|pl|highway|hwy|freeway|fwy|parkway|pkwy|terrace|ter|trail|trl)'

# Directional prefixes/suffixes
DIRECTIONS = r'(?:north|south|east|west|n|s|e|w|ne|nw|se|sw)'

# Common intersection words
INTERSECTION_WORDS = r'(?:and|&|at|near|by|corner\s+of|intersection\s+of)'

# Business/location indicators
BUSINESS_INDICATORS = r'(?:at\s+the|behind|in\s+front\s+of|next\s+to|across\s+from|parking\s+lot\s+of)'


class LocationExtractor:
    """Extract location mentions from transcript text."""

    # Compiled patterns for efficiency
    PATTERNS = [
        # Full address: "123 Main Street" or "123 N Main St"
        (
            rf'\b(\d{{1,5}}\s+{DIRECTIONS}?\s*[\w\s]{{2,30}}\s+{STREET_SUFFIXES})\b',
            'address',
            0.9
        ),
        # Intersection: "Main St and 1st Ave" or "Main & First"
        (
            rf'\b([\w\s]{{2,25}}\s+{STREET_SUFFIXES}\s+{INTERSECTION_WORDS}\s+[\w\s]{{2,25}}\s+{STREET_SUFFIXES})\b',
            'intersection',
            0.85
        ),
        # Street only: "on Main Street" or "heading down Highway 75"
        (
            rf'\b(?:on|heading|traveling|turning\s+onto)\s+([\w\s]{{2,25}}\s+{STREET_SUFFIXES})\b',
            'street',
            0.7
        ),
        # Highway/Interstate: "I-35" or "Highway 380" or "US 75"
        (
            r'\b((?:I|Interstate|Highway|Hwy|US|State\s+Highway|SH|FM|CR)\s*-?\s*\d{1,4})\b',
            'street',
            0.8
        ),
        # Business with indicator: "at the Walmart" or "behind the gas station"
        (
            rf'{BUSINESS_INDICATORS}\s+([\w\s\']{2,30})',
            'business',
            0.6
        ),
        # Named locations/landmarks: "at Prosper Town Center" or "near the school"
        (
            r'\b(?:at|near)\s+(?:the\s+)?([\w\s]{3,30}(?:center|mall|plaza|park|school|church|hospital|station|building|complex|apartments?))\b',
            'landmark',
            0.65
        ),
        # Mile marker: "mile marker 42" or "MM 156"
        (
            r'\b((?:mile\s+marker|mm)\s*\d{1,3})\b',
            'landmark',
            0.75
        ),
        # Cross streets short form: "at 5th and Main"
        (
            rf'\bat\s+(\d{{1,3}}(?:st|nd|rd|th)?\s+{INTERSECTION_WORDS}\s+[\w]+)\b',
            'intersection',
            0.7
        ),
    ]

    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), loc_type, confidence)
            for pattern, loc_type, confidence in self.PATTERNS
        ]

    def extract(self, text: str) -> List[ExtractedLocation]:
        """
        Extract location mentions from transcript text.

        Returns list of ExtractedLocation objects sorted by confidence.
        """
        if not text:
            return []

        locations = []
        seen_texts = set()  # Avoid duplicates

        for pattern, loc_type, base_confidence in self.compiled_patterns:
            for match in pattern.finditer(text):
                raw_text = match.group(1).strip()

                # Clean up the extracted text
                raw_text = self._clean_location_text(raw_text)

                if not raw_text or len(raw_text) < 3:
                    continue

                # Skip if we've already extracted this text
                normalized = raw_text.lower()
                if normalized in seen_texts:
                    continue
                seen_texts.add(normalized)

                # Adjust confidence based on text quality
                confidence = self._adjust_confidence(raw_text, loc_type, base_confidence)

                locations.append(ExtractedLocation(
                    raw_text=raw_text,
                    location_type=loc_type,
                    confidence=confidence
                ))

        # Sort by confidence descending
        locations.sort(key=lambda x: x.confidence, reverse=True)

        return locations

    def _clean_location_text(self, text: str) -> str:
        """Clean and normalize extracted location text."""
        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove trailing punctuation
        text = text.rstrip('.,;:')

        # Capitalize properly
        text = self._title_case_location(text)

        return text

    def _title_case_location(self, text: str) -> str:
        """Title case with handling for abbreviations."""
        words = text.split()
        result = []

        for i, word in enumerate(words):
            lower = word.lower()
            # Keep abbreviations uppercase
            if lower in ('i', 'us', 'sh', 'fm', 'cr', 'hwy', 'ne', 'nw', 'se', 'sw', 'n', 's', 'e', 'w'):
                result.append(word.upper())
            # Handle ordinals
            elif re.match(r'^\d+(st|nd|rd|th)$', lower):
                result.append(lower)
            # Title case everything else
            else:
                result.append(word.capitalize())

        return ' '.join(result)

    def _adjust_confidence(self, text: str, loc_type: str, base_confidence: float) -> float:
        """Adjust confidence based on text characteristics."""
        confidence = base_confidence

        # Boost for longer, more specific text
        word_count = len(text.split())
        if word_count >= 4:
            confidence += 0.05
        elif word_count <= 2:
            confidence -= 0.1

        # Boost for numbers (usually more specific)
        if re.search(r'\d', text):
            confidence += 0.05

        # Penalize very short text
        if len(text) < 10:
            confidence -= 0.1

        # Ensure confidence stays in valid range
        return max(0.1, min(1.0, confidence))

    def extract_with_context(self, text: str, window_size: int = 50) -> List[Tuple[ExtractedLocation, str]]:
        """
        Extract locations with surrounding context.

        Returns list of (ExtractedLocation, context_snippet) tuples.
        """
        if not text:
            return []

        results = []
        locations = self.extract(text)

        for location in locations:
            # Find the location in original text
            idx = text.lower().find(location.raw_text.lower())
            if idx >= 0:
                start = max(0, idx - window_size)
                end = min(len(text), idx + len(location.raw_text) + window_size)
                context = text[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."
                results.append((location, context))
            else:
                results.append((location, ""))

        return results


# Singleton instance
extractor = LocationExtractor()


def extract_locations(text: str) -> List[ExtractedLocation]:
    """Convenience function to extract locations from text."""
    return extractor.extract(text)


def extract_locations_with_context(text: str) -> List[Tuple[ExtractedLocation, str]]:
    """Convenience function to extract locations with context."""
    return extractor.extract_with_context(text)
