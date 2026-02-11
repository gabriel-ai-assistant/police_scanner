"""Tests for location extraction module."""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extractor import LocationExtractor, extract_locations


class TestLocationExtractor:
    """Tests for LocationExtractor class."""

    def setup_method(self):
        self.extractor = LocationExtractor()

    def test_extract_full_address(self):
        """Test extraction of full street address."""
        text = "Unit responding to 123 Main Street for a disturbance."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1
        assert any("123 Main Street" in loc.raw_text for loc in locations)
        assert any(loc.location_type == 'address' for loc in locations)

    def test_extract_address_with_direction(self):
        """Test extraction of address with directional prefix."""
        text = "Car accident at 456 North Oak Avenue."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1
        assert any("North Oak Avenue" in loc.raw_text for loc in locations)

    def test_extract_intersection(self):
        """Test extraction of intersection."""
        text = "Traffic light out at Main Street and 5th Avenue."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1
        assert any(loc.location_type == 'intersection' for loc in locations)

    def test_extract_highway(self):
        """Test extraction of highway references."""
        text = "Vehicle stopped on I-35 northbound."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1
        assert any("I-35" in loc.raw_text.upper() for loc in locations)

    def test_extract_state_highway(self):
        """Test extraction of state highway."""
        text = "Accident on Highway 380 near mile marker 42."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1

    def test_extract_business_location(self):
        """Test extraction of business references."""
        text = "Shoplifter at the Walmart on Preston Road."
        locations = self.extractor.extract(text)
        # Should find the street reference
        assert len(locations) >= 1

    def test_extract_landmark(self):
        """Test extraction of landmarks."""
        text = "Meeting at Prosper Town Center parking lot."
        locations = self.extractor.extract(text)
        assert len(locations) >= 1
        assert any(loc.location_type == 'landmark' for loc in locations)

    def test_no_locations_in_empty_text(self):
        """Test that empty text returns no locations."""
        assert self.extractor.extract("") == []
        assert self.extractor.extract(None) == []

    def test_no_duplicate_extractions(self):
        """Test that same location isn't extracted twice."""
        text = "Go to 123 Main Street. Repeat, 123 Main Street."
        locations = self.extractor.extract(text)
        raw_texts = [loc.raw_text.lower() for loc in locations]
        # Should not have duplicates
        assert len(raw_texts) == len(set(raw_texts))

    def test_confidence_scoring(self):
        """Test that confidence scores are in valid range."""
        text = "Unit 5 to 789 West Oak Boulevard for a welfare check."
        locations = self.extractor.extract(text)
        for loc in locations:
            assert 0.0 <= loc.confidence <= 1.0

    def test_sorted_by_confidence(self):
        """Test that results are sorted by confidence descending."""
        text = "Accident at 123 Main St and Oak Avenue, suspect heading toward the school."
        locations = self.extractor.extract(text)
        if len(locations) > 1:
            confidences = [loc.confidence for loc in locations]
            assert confidences == sorted(confidences, reverse=True)


class TestExtractLocationsFunction:
    """Tests for convenience function."""

    def test_convenience_function_works(self):
        """Test that extract_locations function works."""
        locations = extract_locations("Fire at 100 Elm Street.")
        assert len(locations) >= 1
        assert locations[0].raw_text is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
