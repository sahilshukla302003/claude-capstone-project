from scripts.verify import AC_IDS, check_slow_results, find_missing_acs


def junit(*cases: str) -> str:
    return f"<testsuites><testsuite>{''.join(cases)}</testsuite></testsuites>"


OK_16 = '<testcase name="test_ac16_variant_a"/>'
SKIPPED = '<testcase name="test_ac16_variant_b"><skipped/></testcase>'
FAILED = '<testcase name="test_other"><failure/></testcase>'


def test_all_ac_ids_present_passes() -> None:
    text = " ".join(f'"""AC-{n}"""' for n in range(1, 19))
    assert find_missing_acs(text) == []


def test_missing_ac_id_fails() -> None:
    text = " ".join(f"def test_ac{n}_x" for n in range(1, 19) if n != 7)
    assert find_missing_acs(text) == ["AC-7"]


def test_ac1_not_satisfied_by_ac10() -> None:
    assert "AC-1" in find_missing_acs("AC-10 AC-11")


def test_ac_ids_constant() -> None:
    assert len(AC_IDS) == 18


def test_slow_pass() -> None:
    assert check_slow_results(junit(OK_16)) == []


def test_slow_empty_fails() -> None:
    assert check_slow_results(junit()) == ["no slow tests were executed"]


def test_slow_skipped_fails() -> None:
    assert any("skipped" in p for p in check_slow_results(junit(OK_16, SKIPPED)))


def test_slow_failure_fails() -> None:
    assert any("failed" in p for p in check_slow_results(junit(OK_16, FAILED)))


def test_ac16_absent_fails() -> None:
    problems = check_slow_results(junit('<testcase name="test_something"/>'))
    assert "AC-16 did not run in the slow step" in problems
