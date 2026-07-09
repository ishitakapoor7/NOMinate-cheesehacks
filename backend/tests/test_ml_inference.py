"""Unit tests for the engine's pure inference helpers — no model load needed."""
import numpy as np
import pytest

from ml.recommender import allergy_conflict, matches_allergen, sample_top_k


class TestAllergenMatching:
    def test_exact_match(self):
        assert matches_allergen("peanut", "peanut")

    def test_allergen_inside_compound_ingredient(self):
        assert matches_allergen("peanut butter", "peanut")

    def test_plural_allergen_matches_singular_ingredient(self):
        assert matches_allergen("peanut butter", "peanuts")

    def test_singular_allergen_matches_plural_ingredient(self):
        assert matches_allergen("crushed peanuts", "peanut")

    def test_case_insensitive(self):
        assert matches_allergen("Shrimp Paste", "shrimp")

    def test_no_match(self):
        assert not matches_allergen("chicken breast", "peanut")

    def test_empty_allergen_never_matches(self):
        assert not matches_allergen("chicken", "")


class TestAllergyConflict:
    def test_conflict_in_pipe_delimited_ingredients(self):
        assert allergy_conflict("flour|peanut oil|sugar", ["peanuts"])

    def test_no_conflict(self):
        assert not allergy_conflict("flour|butter|sugar", ["shellfish"])

    def test_multiple_allergens_any_hit(self):
        assert allergy_conflict("rice|shrimp|scallion", ["peanuts", "shrimp"])

    def test_empty_allergies(self):
        assert not allergy_conflict("peanut|shrimp", [])
        assert not allergy_conflict("peanut|shrimp", None)


class TestSampleTopK:
    def test_only_picks_from_top_k(self):
        scores = np.array([1.0, 5.0, 4.0, -np.inf, 4.5, 0.5])
        rng = np.random.default_rng(0)
        picks = {sample_top_k(scores, k=3, rng=rng) for _ in range(200)}
        assert picks <= {1, 2, 4}  # the three highest valid scores
        assert len(picks) > 1  # and it genuinely varies

    def test_never_picks_filtered_dish(self):
        scores = np.array([-np.inf, 2.0, -np.inf])
        rng = np.random.default_rng(0)
        assert all(sample_top_k(scores, k=5, rng=rng) == 1 for _ in range(20))

    def test_all_filtered_raises(self):
        with pytest.raises(ValueError):
            sample_top_k(np.array([-np.inf, -np.inf]), k=5)
