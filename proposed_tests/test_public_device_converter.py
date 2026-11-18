"""Public CLI regression: no private run fixtures or model credentials needed."""

from pathlib import Path
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]


class PublicDeviceConverter(unittest.TestCase):
    def test_device_converter_help_loads(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "scorers/convert_device.py"), "--help"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
