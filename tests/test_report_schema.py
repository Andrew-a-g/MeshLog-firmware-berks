import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MY_MESH = ROOT / "src" / "meshlog" / "mesh" / "MyMesh.h"
NODE_PREFS = ROOT / "src" / "meshlog" / "mesh" / "NodePrefs.h"


class ReportSchemaCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.mesh_source = MY_MESH.read_text(encoding="utf-8")
        self.prefs_source = NODE_PREFS.read_text(encoding="utf-8")

    def test_normal_reports_use_legacy_schema_v1(self):
        self.assertNotIn("MESHLOG_VERSION", self.mesh_source)
        self.assertEqual(self.mesh_source.count('doc["version"] = 1;'), 5)

    def test_raw_reports_use_legacy_split_packet_fields(self):
        for field in ("header", "path", "payload", "snr", "hash_size", "decoded"):
            self.assertIn(f'doc["packet"]["{field}"]', self.mesh_source)
        self.assertNotIn('doc["packet"]["raw"]', self.mesh_source)

    def test_raw_upload_remains_operator_controlled(self):
        self.assertIn("uint8_t doraw;", self.prefs_source)
        self.assertIn("if (_logp.doraw)", self.mesh_source)
        self.assertIn('memcmp(config, "raw ", 4)', self.mesh_source)


if __name__ == "__main__":
    unittest.main()
