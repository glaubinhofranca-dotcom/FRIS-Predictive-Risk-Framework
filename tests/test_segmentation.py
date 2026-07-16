import numpy as np
import pandas as pd

from fris_segmentation import _segment


def _df(values, defaults):
    return pd.DataFrame({"group": values, "default_flag": defaults})


def test_segment_filters_groups_below_min_n():
    # 8 in group A (clears min_n=5), 3 in group B (does not).
    values = ["A"] * 8 + ["B"] * 3
    defaults = [1, 0, 0, 0, 0, 0, 0, 0] + [1, 0, 0]
    g = _segment(_df(values, defaults), "group", "Group", min_n=5)
    assert list(g["Group"]) == ["A"]
    assert g.iloc[0]["n"] == 8


def test_segment_falls_back_to_unfiltered_when_all_groups_below_min_n():
    # Every group has n=2, none clears min_n=5 — must not return empty.
    values = ["A", "A", "B", "B", "C", "C"]
    defaults = [1, 0, 1, 0, 0, 0]
    g = _segment(_df(values, defaults), "group", "Group", min_n=5)
    assert not g.empty
    assert set(g["Group"]) == {"A", "B", "C"}


def test_segment_caps_fallback_at_top_15_by_count():
    # 30 distinct near-unique values (high-cardinality free text column);
    # none clears min_n, so the fallback must cap the result, not dump all 30.
    rng = np.random.default_rng(0)
    values = [f"plan-{i}" for i in range(30)]
    defaults = rng.integers(0, 2, size=30).tolist()
    g = _segment(_df(values, defaults), "group", "Group", min_n=5)
    assert len(g) <= 15


def test_segment_returns_empty_when_column_entirely_null():
    values = [np.nan, np.nan, np.nan]
    defaults = [0, 1, 0]
    g = _segment(_df(values, defaults), "group", "Group", min_n=5)
    assert g.empty
