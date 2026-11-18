# A public device-converter entry point fails before reading any input

Audit for [Poidh bounty 1520](https://poidh.xyz/base/bounty/1520).

## Finding

At `r4topunk/boar-bench` commit
`b41a25acfabf89f1d015103ca1329554f985a257`, the documented device
conversion command cannot start:

```text
$ python3 scorers/convert_device.py --help
ModuleNotFoundError: No module named 'scorers.convert_legacy'
```

The failure occurs before argument parsing, input-file access, a phone connection,
or an inference request. Installing model weights or providing private run
fixtures cannot resolve the missing in-repository Python module.

The public Python test stages nevertheless pass. A new, fixture-free CLI smoke
test catches the missing import. This makes the problem both a concrete release
omission and a narrow regression-coverage gap.

## What was checked

The checkout was pinned and unmodified. The accompanying `reproduce.py` records
the commands, return codes, source hashes and stdout/stderr in
`evidence/observations.json` and `evidence/observations.log`.
Only local checkout paths are normalized in the recorded diagnostic text.

| Check | Observation |
| --- | --- |
| `python3 scorers/convert_device.py --help` | Exit 1: missing `scorers.convert_legacy` |
| `python3 scorers/score.py --help` | Exit 0: a working same-environment control |
| Public scorer Python test stage | 40 tests, OK, 2 skipped |
| Public harness Python test stage | 8 tests, OK, 2 skipped |
| Proposed fixture-free converter smoke test | 1 test, fails with the same missing-module error |
| Original upstream checkout | Left unchanged |

These are local execution results, not a physical-device run.
The regression was applied and exercised only in a disposable local clone.
The observation renderer creates a labeled summary image; it is not presented
as an unedited terminal screenshot.

## Why this matters

The public [device kit, lines 14-25](https://github.com/r4topunk/boar-bench/blob/b41a25acfabf89f1d015103ca1329554f985a257/devices/DEVICE-KIT.md#L14-L25)
describes `convert_device.py` as the bridge from device answer rows to the
`EvalTrace` contract. Its
[scoring instructions, lines 237-265](https://github.com/r4topunk/boar-bench/blob/b41a25acfabf89f1d015103ca1329554f985a257/devices/DEVICE-KIT.md#L237-L265)
start with this converter.

But [the converter imports an absent helper at line 32](https://github.com/r4topunk/boar-bench/blob/b41a25acfabf89f1d015103ca1329554f985a257/scorers/convert_device.py#L32).
The public tree contains neither `scorers/convert_legacy.py` nor the
`scorers/tests/test_convert_device.py` file described as containing 10 tests in
the [device-kit file inventory](https://github.com/r4topunk/boar-bench/blob/b41a25acfabf89f1d015103ca1329554f985a257/devices/DEVICE-KIT.md#L321-L333).

Consequently, a third party following the documented workflow cannot convert
their own fresh iOS/Android answer-pipeline rows using this release. The later
judging, comparison and reporting steps do not get an `EvalTrace` file from that
entry point.

The existing Python test command is
[two unittest discovery stages](https://github.com/r4topunk/boar-bench/blob/b41a25acfabf89f1d015103ca1329554f985a257/package.json#L9-L13).
Neither surviving public stage imports this converter.
This is not an objection to intentionally withholding private fixtures:
the proposed smoke test requires no fixtures at all.

## Reproduce

Prerequisites: Python 3, Node.js for the existing scorer tests, and Git.
No inference credentials, model download, phone, package installation,
wallet connection or payment is needed.

```bash
git clone https://github.com/r4topunk/boar-bench.git upstream/boar-bench
git -C upstream/boar-bench checkout b41a25acfabf89f1d015103ca1329554f985a257
python3 reproduce.py --repo upstream/boar-bench
```

The script exits 0 when all stated observations are confirmed. That exit code
means **the defect was reproduced**, not that conversion succeeded.

Its regression-test phase copies the pinned repository to a temporary directory,
applies `regression-guard.patch`, and executes the new public smoke test.
The original checkout is not modified.

`evidence/finding.png` is already rendered. Regenerating it with
`python3 render_evidence.py` additionally requires Pillow; this is optional and
not needed to reproduce the defect.

For just the primary finding:

```bash
cd upstream/boar-bench
python3 scorers/convert_device.py --help
```

## Repair recommendation

1. Publish the original `scorers/convert_legacy.py` required by this release,
   or replace the import with a complete, explicitly documented device-row
   mapper maintained in this repository.
2. Publish the advertised converter tests, with synthetic non-sensitive rows
   where private fixtures cannot be released. Cover source/citation mapping,
   timeouts, re-asks and model fallbacks against the real `EvalTrace` schema.
3. Keep the fixture-independent CLI smoke test in ordinary `test:py` discovery.
   The accompanying `regression-guard.patch` supplies that test.

The supplied patch is **a regression guard, not a converter implementation**.
It intentionally fails on the affected release. It would be misleading to
silently stub out the missing mapping or invent historical telemetry and call
that a faithful restoration.

## Scope and prior work

This affects the documented historical iOS/Android device-kit entry point.
It does not prove that the private original converter was wrong, change any
published scores, or overturn the final LabRat phone result. Already-converted
traces can still be scored by the separate working scorer.

The initial local screening on 17 November 2026 checked the titles and
descriptions of all 37 then-listed bounty claims for converter-specific terms;
no match was found. A pre-publication recheck on 18 November found 38 claims.
The new claim, 9711, concerns inclusion of benchmark anchors in the scoring
denominator, not this missing converter.
This is not an exhaustive novelty claim over their off-site artifacts.
[Upstream issue 1](https://github.com/r4topunk/boar-bench/issues/1) concerns
last-trace precedence in judge preflight, not this missing device converter.
The earlier raw-ratio/scorer finding was already fixed upstream and is not
reused here.

All analysis and reproductions here use public sources. No phone execution,
paid model judging, upstream issue/PR, bounty claim or blockchain transaction
has been performed for this submission.

Upstream code and diagnostic excerpts are attributed to r4to's MIT-licensed
`boar-bench`; its notice is included as `UPSTREAM-LICENSE.txt`.
