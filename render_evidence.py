#!/usr/bin/env python3
"""Render a labeled summary of recorded executions, not a simulated terminal."""

import argparse
import json
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent


def font(size):
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "evidence/observations.json")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/finding.png")
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    image = Image.new("RGB", (1600, 1150), "#f3f6fa")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 168), fill="#10223a")
    draw.text((52, 34), "BOAR: public device converter cannot start", font=font(32), fill="white")
    draw.text((52, 98), f"Pinned source: {data['commit']}", font=font(20), fill="#b9d1ef")
    y = 206
    sections = [
        (
            "1. Actual failure: no phone, input file or model needed",
            "python3 scorers/convert_device.py --help\n"
            + data["commands"]["converter_help"]["stderr"].strip().splitlines()[-1]
            + f"\nExit: {data['commands']['converter_help']['returncode']}",
            "#8c2130",
        ),
        (
            "2. The public Python test command does not detect it",
            "scorers/tests: 40 tests, OK (2 skipped)\n"
            "harness/tests: 8 tests, OK (2 skipped)\n"
            "Tracked: convert_device.py. Not tracked: convert_legacy.py\n"
            "The 10 converter tests named by DEVICE-KIT.md are not published.",
            "#203950",
        ),
        (
            "3. A fixture-free regression catches the release defect",
            "Added one --help smoke test in a disposable checkout.\n"
            "Result: 1 test, FAILED; same missing-module error.\n"
            "Original checkout left unchanged. No inference API invoked.",
            "#203950",
        ),
        (
            "Scope: a reproducibility defect, not an overturned result",
            "Affects the documented historical device kit.\n"
            "Does not establish that the final phone scores are wrong.\n"
            "No conversion fix or physical-phone test is being claimed.",
            "#203950",
        ),
    ]
    for title, body, color in sections:
        draw.text((52, y), title, font=font(23), fill=color)
        y += 42
        for line in body.splitlines():
            for wrapped in textwrap.wrap(line, width=112) or [""]:
                draw.text((60, y), wrapped, font=font(19), fill="#23374d")
                y += 29
        y += 28
    draw.text(
        (52, 1104),
        "Generated evidence summary from observations.json; not a native terminal or phone screenshot.",
        font=font(16),
        fill="#56677a",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
