import json
import subprocess
import sys


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "forgejury", *args],
        capture_output=True,
        text=True,
    )


def test_lint_cli_warns_but_exits_zero():
    proc = _run("lint", "examples/SPEC.md")
    assert proc.returncode == 0
    assert "WARNING" in proc.stdout
    assert "volatile" in proc.stdout


def test_lint_cli_errors_on_missing_spec():
    proc = _run("lint", "examples/does-not-exist.md")
    assert proc.returncode == 2
    assert "ERROR" in proc.stderr


def test_grade_cli_fails_when_a_build_lies_and_shows_divergence():
    proc = _run("grade", "examples/SPEC.md", "examples/build-a", "examples/build-b", "examples/build-c")
    assert proc.returncode == 1
    assert "Summary: 2/3 builds PASS" in proc.stdout
    assert "FAIL  build-b: claims:files, claims:tests_passed" in proc.stdout
    assert "2-1" in proc.stdout
    assert "build-c" in proc.stdout


def test_grade_cli_claims_advisory_does_not_fail_a_lying_build():
    proc = _run("grade", "examples/SPEC.md", "examples/build-a", "examples/build-b",
                "examples/build-c", "--claims-advisory")
    assert proc.returncode == 0
    assert "Summary: 3/3 builds PASS" in proc.stdout


def test_grade_cli_exits_zero_when_every_build_is_honest():
    proc = _run("grade", "examples/SPEC.md", "examples/build-a", "examples/build-c")
    assert proc.returncode == 0


def test_grade_cli_json_is_valid_and_matches_schema():
    proc = _run(
        "grade", "examples/SPEC.md",
        "examples/build-a", "examples/build-b", "examples/build-c", "--json",
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert "builds" in report and "consensus" in report and "summary" in report
    assert report["summary"]["failed"] == {"examples/build-b": ["claims:files", "claims:tests_passed"]}
    for build in report["builds"]:
        assert set(build) >= {"build", "spec_axis", "claims_axis", "verdict", "reasons"}
        assert build["verdict"] in {"PASS", "FAIL"}
    for fixture in report["consensus"].values():
        assert "diverging_build" in fixture
        assert fixture["label"] in {"3-0", "2-1", "3-way"}


def test_grade_cli_no_args_shows_usage():
    proc = _run()
    assert proc.returncode != 0
    assert "usage" in proc.stderr.lower()
