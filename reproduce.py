#!/usr/bin/env python3
"""Reproduce the public device-converter failure without inference or device data."""

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
PIN = "b41a25acfabf89f1d015103ca1329554f985a257"
TEST_PATH = "scorers/tests/test_public_device_converter.py"


def run(command, cwd, replacements=()):
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=cwd,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = {"stdout": result.stdout, "stderr": result.stderr}
    for key in output:
        for before, after in replacements:
            output[key] = output[key].replace(str(before), after)
    return {
        "command": command,
        "returncode": result.returncode,
        "seconds": round(time.monotonic() - started, 3),
        **output,
    }


def inspect_claims(path):
    if not path.exists():
        return {"available": False}
    data = json.loads(path.read_text())
    terms = ("convert_device", "convert_legacy", "device converter", "device-conversion")
    matches = [
        claim["claimId"]
        for claim in data.get("claims", [])
        if any(
            term in (claim.get("title", "") + "\n" + claim.get("description", "")).lower()
            for term in terms
        )
    ]
    return {
        "available": True,
        "claim_count": len(data.get("claims", [])),
        "searched_terms": terms,
        "matching_claim_ids": matches,
        "scope": "Titles and descriptions only; off-site artifacts not exhaustively reviewed.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT / "upstream/boar-bench")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/observations.json")
    args = parser.parse_args()
    repo = args.repo.resolve()
    replacements = ((repo, "<boar-bench>"),)
    commit = run(["git", "rev-parse", "HEAD"], repo)
    if commit["returncode"] or commit["stdout"].strip() != PIN:
        parser.error(f"--repo must be checked out at {PIN}")
    before = run(["git", "status", "--porcelain"], repo)
    if before["returncode"] or before["stdout"].strip():
        parser.error("--repo must be an unmodified checkout")

    commands = {
        "python_version": [sys.executable, "--version"],
        "converter_help": [sys.executable, "scorers/convert_device.py", "--help"],
        "scorer_help": [sys.executable, "scorers/score.py", "--help"],
        "scorer_tests": [
            sys.executable, "-m", "unittest", "discover", "-s", "scorers/tests", "-t", ".", "-q"
        ],
        "harness_tests": [
            sys.executable, "-m", "unittest", "discover", "-s", "harness/tests", "-t", ".", "-q"
        ],
    }
    results = {
        name: run(command, repo, replacements)
        for name, command in commands.items()
    }
    tracked = run(
        ["git", "ls-files", "scorers/convert*", "scorers/tests/test_convert*"], repo
    )["stdout"].splitlines()
    files = [
        "scorers/convert_device.py",
        "devices/DEVICE-KIT.md",
        "package.json",
        "packages/protocol/src/index.ts",
    ]
    hashes = {
        name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
        for name in files
    }
    test = ROOT / "proposed_tests/test_public_device_converter.py"
    patch = ROOT / "regression-guard.patch"
    patch.write_text(
        f"diff --git a/{TEST_PATH} b/{TEST_PATH}\nnew file mode 100644\n"
        + "".join(difflib.unified_diff(
            [], test.read_text().splitlines(keepends=True),
            fromfile="/dev/null", tofile=f"b/{TEST_PATH}",
        ))
    )
    with tempfile.TemporaryDirectory(prefix="poidh-1520-regression-") as directory:
        temporary = Path(directory) / "bench"
        clone = run(["git", "clone", "--quiet", "--no-hardlinks", str(repo), str(temporary)], ROOT)
        if clone["returncode"]:
            raise RuntimeError("Could not create disposable regression-test checkout")
        applied = run(["git", "apply", str(patch)], temporary)
        if applied["returncode"]:
            raise RuntimeError(applied["stderr"])
        regression = run(
            [sys.executable, "-m", "unittest", "scorers.tests.test_public_device_converter", "-q"],
            temporary,
            ((temporary, "<guard-checkout>"),),
        )
    after = run(["git", "status", "--porcelain"], repo)
    failure = results["converter_help"]
    checks = {
        "pinned_commit": commit["stdout"].strip() == PIN,
        "missing_helper_not_tracked": "scorers/convert_legacy.py" not in tracked,
        "documented_converter_tests_not_tracked": "scorers/tests/test_convert_device.py" not in tracked,
        "converter_fails_at_missing_import": (
            failure["returncode"] != 0
            and "ModuleNotFoundError" in failure["stderr"]
            and "scorers.convert_legacy" in failure["stderr"]
        ),
        "other_scorer_help_succeeds": results["scorer_help"]["returncode"] == 0,
        "published_scorer_test_stage_succeeds": results["scorer_tests"]["returncode"] == 0,
        "published_harness_test_stage_succeeds": results["harness_tests"]["returncode"] == 0,
        "new_fixture_free_regression_catches_it": (
            regression["returncode"] != 0
            and "ModuleNotFoundError" in regression["stderr"]
            and "scorers.convert_legacy" in regression["stderr"]
            and "Ran 1 test" in regression["stderr"]
        ),
        "upstream_checkout_unchanged": after["returncode"] == 0 and not after["stdout"].strip(),
    }
    observation = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/r4topunk/boar-bench",
        "commit": PIN,
        "checkout_paths_normalized": True,
        "tracked_conversion_files": tracked,
        "source_sha256": hashes,
        "commands": results,
        "regression_test": regression,
        "checks": checks,
        "novelty_screen": inspect_claims(ROOT / "evidence/bounty-1520.json"),
        "scope": (
            "Public historical device-conversion tooling only. No phone run, "
            "new model judgments, headline-score recomputation, publication or payment."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(observation, indent=2) + "\n")
    log = []
    for name, result in [*results.items(), ("proposed_regression", regression)]:
        log.extend([
            f"=== {name} ===",
            "$ " + " ".join(result["command"]),
            f"exit: {result['returncode']}",
            result["stdout"].rstrip(),
            result["stderr"].rstrip(),
            "",
        ])
    args.out.with_suffix(".log").write_text("\n".join(log))
    for name, passed in checks.items():
        print(f"{'CONFIRMED' if passed else 'NOT CONFIRMED'} {name}")
    print(f"Evidence: {args.out}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
