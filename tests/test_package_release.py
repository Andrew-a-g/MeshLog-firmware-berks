import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.package_release import (
    BOARDS,
    PROVENANCE_FILE,
    package,
    sha256,
    validate_repository,
)


COMMIT = "abcdef0123456789abcdef0123456789abcdef01"
EPOCH = 1_700_000_000


class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.build = self.root / "build"
        for index, (_, _, environment) in enumerate(BOARDS):
            directory = self.build / environment
            directory.mkdir(parents=True)
            (directory / "firmware-merged.bin").write_bytes(bytes([index]) * (index + 1))
            provenance = {
                "schema_version": 1,
                "environment": environment,
                "git_commit": COMMIT,
                "source_date_epoch": EPOCH,
                "source_tree_clean": True,
            }
            (directory / PROVENANCE_FILE).write_text(
                json.dumps(provenance), encoding="utf-8"
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_manifest_checksums_include_manifest(self):
        output = self.root / "candidate"
        manifest = package(self.build, output, "1.5.0-dev.abcdef0", COMMIT, EPOCH)
        manifest_bytes = (output / "manifest.json").read_bytes()
        sums = (output / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertEqual(manifest, json.loads(manifest_bytes))
        self.assertEqual(manifest["release_status"], "UNVALIDATED")
        self.assertTrue(manifest["source_tree_clean"])
        self.assertEqual(len(manifest["files"]), len(BOARDS))
        for item in manifest["files"]:
            artifact = output / item["filename"]
            self.assertEqual(item["sha256"], sha256(artifact))
            self.assertEqual(item["size"], artifact.stat().st_size)
            self.assertEqual(item["build_provenance"]["git_commit"], COMMIT)
            self.assertIn(f"{item['sha256']}  {item['filename']}\n", sums)
        self.assertIn(f"{sha256(output / 'manifest.json')}  manifest.json\n", sums)

    def test_existing_output_is_never_replaced_or_deleted(self):
        output = self.root / "candidate"
        output.mkdir()
        sentinel = output / "keep-me"
        sentinel.write_text("important", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            package(self.build, output, "test", COMMIT, EPOCH)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "important")

    def test_missing_board_fails_without_partial_bundle(self):
        missing = self.build / BOARDS[-1][2] / "firmware-merged.bin"
        missing.unlink()
        output = self.root / "candidate"
        with self.assertRaisesRegex(FileNotFoundError, BOARDS[-1][2]):
            package(self.build, output, "test", COMMIT, EPOCH)
        self.assertFalse(output.exists())

    def test_stale_or_dirty_build_provenance_is_rejected(self):
        environment = BOARDS[0][2]
        marker = self.build / environment / PROVENANCE_FILE
        provenance = json.loads(marker.read_text(encoding="utf-8"))
        provenance["git_commit"] = "0" * 40
        marker.write_text(json.dumps(provenance), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, environment):
            package(self.build, self.root / "candidate", "test", COMMIT, EPOCH)
        self.assertFalse((self.root / "candidate").exists())

    def test_invalid_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            package(self.build, self.root / "candidate", "bad version", "abcdef1", 0)

    def test_repository_must_be_exact_head_and_clean(self):
        repo = self.root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "tracked").write_text("ok", encoding="utf-8")
        subprocess.run(["git", "add", "tracked"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "test"], cwd=repo, check=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        validate_repository(repo, head)
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validate_repository(repo, "0" * 40)
        (repo / "untracked").write_text("dirty", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "dirty"):
            validate_repository(repo, head)


if __name__ == "__main__":
    unittest.main()
