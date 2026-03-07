"""Tests for sweep_params registry: SweepParam, generate_values, get_param."""

from __future__ import annotations

import pytest

from compute_permit_sim.schemas.sweep_params import (
    SWEEPABLE_PARAMS,
    SweepParam,
    categories,
    generate_values,
    get_param,
    params_for_category,
)


class TestRegistry:
    def test_at_least_ten_params(self) -> None:
        assert len(SWEEPABLE_PARAMS) >= 10

    def test_all_have_required_fields(self) -> None:
        for p in SWEEPABLE_PARAMS:
            assert p.path
            assert p.label
            assert p.unit is not None
            assert p.category
            assert p.default_min <= p.default_max
            assert p.default_step > 0

    def test_all_paths_unique(self) -> None:
        paths = [p.path for p in SWEEPABLE_PARAMS]
        assert len(paths) == len(set(paths)), "Duplicate param paths in registry"

    def test_get_param_known_path(self) -> None:
        p = get_param("audit.base_prob")
        assert isinstance(p, SweepParam)
        assert p.label == "Base Audit Rate π₀"

    def test_get_param_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            get_param("nonexistent.param")

    def test_categories_non_empty(self) -> None:
        cats = categories()
        assert len(cats) > 0
        assert "Enforcement" in cats
        assert "Economics" in cats

    def test_params_for_category_enforcement(self) -> None:
        enforcers = params_for_category("Enforcement")
        paths = [p.path for p in enforcers]
        assert "audit.base_prob" in paths

    def test_params_for_category_missing(self) -> None:
        assert params_for_category("NonExistent") == []


class TestGenerateValues:
    def test_default_values_uses_registry(self) -> None:
        p = get_param("audit.base_prob")
        vals = generate_values(p)
        assert vals[0] == p.default_min
        assert min(abs(v - p.default_max) for v in vals) < p.default_step * 0.1

    def test_custom_range(self) -> None:
        p = get_param("audit.base_prob")
        vals = generate_values(p, min_val=0.0, max_val=0.20, step=0.05)
        assert vals[0] == 0.0
        assert len(vals) == 5  # 0.00, 0.05, 0.10, 0.15, 0.20

    def test_single_point_range(self) -> None:
        p = get_param("audit.base_prob")
        vals = generate_values(p, min_val=0.10, max_val=0.10, step=0.05)
        assert vals == [0.10]

    def test_invalid_step_raises(self) -> None:
        p = get_param("audit.base_prob")
        with pytest.raises(ValueError):
            generate_values(p, step=0.0)

    def test_invalid_range_raises(self) -> None:
        p = get_param("audit.base_prob")
        with pytest.raises(ValueError):
            generate_values(p, min_val=0.5, max_val=0.1)

    def test_values_are_rounded(self) -> None:
        p = get_param("audit.base_prob")
        vals = generate_values(p, min_val=0.0, max_val=0.3, step=0.1)
        for v in vals:
            assert v == round(v, 8)

    def test_collateral_range(self) -> None:
        p = get_param("collateral_amount")
        vals = generate_values(p, min_val=0.0, max_val=50.0, step=10.0)
        assert vals[0] == 0.0
        assert vals[-1] == 50.0
        assert len(vals) == 6
