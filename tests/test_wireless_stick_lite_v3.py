"""Keep the Lite V3 experimental build distinct from the validated Heltec V3."""

import configparser
import unittest
from pathlib import Path

from scripts.package_release import BOARDS


ROOT = Path(__file__).resolve().parents[1]
ENV = "Heltec_wireless_stick_lite_v3_meshlog"


class WirelessStickLiteV3Tests(unittest.TestCase):
    def test_distinct_headless_hf_target_not_in_release_matrix(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(ROOT / "variants/heltec_v3/platformio.ini")
        lite = config[f"env:{ENV}"]
        heltec = config["env:Heltec_lora32_v3_meshlog"]
        shared = config["Heltec_lora32_v3"]
        self.assertEqual(lite["extends"], "Heltec_v3_meshlog_base")
        self.assertEqual(heltec["extends"], "Heltec_v3_meshlog_base")
        self.assertIn("-D P_LORA_RESET=12", lite["build_flags"])
        self.assertIn("-D WIRELESS_STICK_LITE_V3=1", lite["build_flags"])
        self.assertIn("-D P_LORA_RESET=RADIOLIB_NC", heltec["build_flags"])
        self.assertNotIn("P_LORA_RESET", shared["build_flags"])
        for signal, pin in {"DIO_1": 14, "NSS": 8, "BUSY": 13,
                            "SCLK": 9, "MOSI": 10, "MISO": 11}.items():
            self.assertIn(f"-D P_LORA_{signal}={pin}", shared["build_flags"])
        self.assertNotIn("DISPLAY_CLASS", shared["build_flags"])
        self.assertNotIn(ENV, [env for _, _, env in BOARDS])


if __name__ == "__main__":
    unittest.main()
