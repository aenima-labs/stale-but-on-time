"""The grading rules and the statistics that the paper's pass rates rest on."""

import numpy as np

import e2_analyze as a


def trial(case, condition, passed, cls="asked-shift"):
    return {"case": case, "condition": condition, "passed": passed, "class": cls}


# ---------------------------------------------------------------- grading rules
def test_key_must_begin_a_word():
    assert a.key_starts_word("She studied with Hayato Mori in Japan.", ["Mori"])
    assert not a.key_starts_word("I don't have any memories about that.", ["Mori"])


def test_key_may_continue_into_a_longer_word():
    assert a.key_starts_word("She regretted it all her life.", ["regret"])
    assert a.key_starts_word("Old Mr Finch made her sew headbands.", ["headband"])


def test_key_match_ignores_case_and_takes_any_key():
    assert a.key_starts_word("it won SECOND PRIZE at the fair", ["Dunmere", "second prize"])
    assert not a.key_starts_word("it won a rosette", ["Dunmere", "second prize"])


def test_numeric_key_does_not_match_inside_a_longer_number():
    assert a.key_starts_word("There were 112 steps.", ["112"])
    assert not a.key_starts_word("That was in 2112.", ["112"])


def test_refusals_in_words_are_recognised():
    for reply in (
        "I don't know which city she stayed in.",
        "I'm not sure; the memories I have don't say.",
        "I have no record of that.",
        "I can't say what her first word was.",
    ):
        assert a.REFUSAL.search(reply), reply


def test_plain_answers_are_not_refusals():
    for reply in (
        "She stayed in Kyoto for three weeks.",
        "Her first word was boat.",
    ):
        assert not a.REFUSAL.search(reply), reply


# ---------------------------------------------------------------- statistics
def test_case_boot_resamples_cases_not_trials():
    # Two cases: one passes all five trials, one none. The mean is 0.5 and, with
    # cases as the unit, the interval spans everything from 0 to 1.
    rows = [trial("x", "c", True)] * 5 + [trial("y", "c", False)] * 5
    mean, lo, hi = a.case_boot(rows, "passed", np.random.default_rng(1))
    assert mean == 0.5
    assert lo == 0.0 and hi == 1.0


def test_case_boot_has_no_width_when_cases_agree():
    rows = [trial(c, "c", i < 3) for c in "abcd" for i in range(5)]
    mean, lo, hi = a.case_boot(rows, "passed", np.random.default_rng(1))
    assert abs(mean - 0.6) < 1e-12 and abs(lo - 0.6) < 1e-12 and abs(hi - 0.6) < 1e-12


def test_paired_diff_pairs_within_case():
    # Condition p beats q by exactly 0.2 in every case, at very different levels.
    rows = []
    for case, base in (("a", 0), ("b", 2), ("c", 4)):
        rows += [trial(case, "q", i < base) for i in range(5)]
        rows += [trial(case, "p", i < base + 1) for i in range(5)]
    mean, lo, hi = a.paired_diff(rows, "p", "q", np.random.default_rng(1))
    assert abs(mean - 0.2) < 1e-12
    assert abs(lo - 0.2) < 1e-12 and abs(hi - 0.2) < 1e-12


def test_case_level_counts_and_sign_flip():
    rows = []
    for i in range(12):  # p ahead in ten cases, level in two
        rows += [trial(f"c{i}", "p", i < 10 or j < 2) for j in range(5)]
        rows += [trial(f"c{i}", "q", i >= 10 and j < 2) for j in range(5)]
    out = a.case_level(rows, "p", "q")
    assert (out["cases"], out["ahead"], out["behind"], out["level"]) == (12, 10, 0, 2)
    assert out["sign_flip_p"] < 0.01


def test_case_level_finds_nothing_in_balanced_noise():
    rows = []
    for i in range(12):  # p ahead in six cases, behind in six, by the same margin
        rows += [trial(f"c{i}", "p", i % 2 == 0) for _ in range(5)]
        rows += [trial(f"c{i}", "q", i % 2 == 1) for _ in range(5)]
    out = a.case_level(rows, "p", "q")
    assert (out["ahead"], out["behind"]) == (6, 6)
    assert out["sign_flip_p"] > 0.9


def test_control_class_is_not_pooled_into_recall():
    assert a.CARRY not in a.NEW_NEED
    assert set(a.NEW_NEED) == {"asked-continuing", "asked-shift", "unprompted"}


# ---------------------------------------------------------------- Experiment 3
def test_unsupported_unprompted_passes_are_counted():
    import e3_analyze as e3

    def row(case, passed, gold, searched, cls="unprompted"):
        return {"case": case, "class": cls, "passed": passed, "gold_in_wm": gold, "searched": searched}

    rows = [
        row("x", True, True, False),    # the memory was loaded
        row("x", True, False, True),    # the model searched
        row("y", True, False, False),   # a key word with nothing behind it
        row("y", False, False, False),  # a failure is not a loose pass
        row("z", True, False, False, cls="asked-shift"),  # other classes are not counted
    ]
    out = e3.unsupported_passes(rows)
    assert out == {"trials": 4, "passed": 3, "unsupported": 1, "unsupported_cases": ["y"]}
