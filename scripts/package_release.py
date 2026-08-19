#!/usr/bin/env python3
"""Create an explicitly unvalidated firmware candidate with verified provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


BOARDS = (
    ("generic-e22", "Generic E22 (ESP32)", "Generic_E22_meshlog"),
    ("heltec-v3", "Heltec WiFi LoRa 32 V3", "Heltec_lora32_v3_meshlog"),
    ("heltec-v4", "Heltec WiFi LoRa 32 V4", "Heltec_v4_meshlog"),
    ("lilygo-t3s3", "LilyGo T3-S3", "LilyGo_T3S3_meshlog"),
    ("lilygo-tlora-v2-1", "LilyGo T-LoRa V2.1", "LilyGo_TLora_v2_1_meshlog"),
    ("xiao-s3-wio", "Seeed XIAO ESP32-S3 + Wio-SX1262", "Xiao_S3_meshlog"),
)
PROVENANCE_FILE = "build-provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def validate_repository(repo_root: Path, commit: str) -> None:
    """Require the requested full revision to be the clean checkout's HEAD."""
    if _git(repo_root, "rev-parse", "HEAD").lower() != commit.lower():
        raise ValueError("--commit must exactly match the checkout's HEAD")
    dirty = _git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise ValueError("refusing to package from a dirty source tree")


def _read_provenance(path: Path, environment: str, commit: str, epoch: int) -> dict:
    try:
        provenance = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"missing build provenance for {environment}: {path}") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"invalid build provenance for {environment}: {error}") from error

    expected = {
        "schema_version": 1,
        "environment": environment,
        "git_commit": commit.lower(),
        "source_date_epoch": epoch,
        "source_tree_clean": True,
    }
    if provenance != expected:
        raise ValueError(
            f"build provenance mismatch for {environment}; clean-rebuild this exact commit"
        )
    return provenance


def package(
    build_root: Path,
    output: Path,
    version: str,
    commit: str,
    epoch: int,
    repo_root: Path | None = None,
) -> dict:
    if not re.fullmatch(r"[0-9A-Fa-f]{40}", commit):
        raise ValueError("commit must be the full 40-character hexadecimal Git commit")
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._+-]*", version):
        raise ValueError("version contains unsupported characters")
    if epoch < 0:
        raise ValueError("source date epoch must not be negative")
    if repo_root is not None:
        validate_repository(repo_root, commit)

    sources = []
    for slug, board, environment in BOARDS:
        environment_dir = build_root / environment
        source = environment_dir / "firmware-merged.bin"
        if not source.is_file():
            raise FileNotFoundError(f"missing merged image for {environment}: {source}")
        provenance = _read_provenance(
            environment_dir / PROVENANCE_FILE, environment, commit, epoch
        )
        sources.append((slug, board, environment, source, provenance))

    # Never recursively delete a caller-selected path. Candidates are immutable:
    # use a new output path/version, or remove an old candidate deliberately.
    if output.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    if output.exists():
        raise FileExistsError(f"output already exists; refusing to replace it: {output}")
    output_parent = output.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output_parent))

    try:
        files = []
        for slug, board, environment, source, provenance in sources:
            filename = f"meshlog-berks-{version}-{slug}-merged.bin"
            destination = staging / filename
            shutil.copyfile(source, destination)
            files.append({
                "board": board,
                "environment": environment,
                "filename": filename,
                "flash_offset": "0x0",
                "sha256": sha256(destination),
                "size": destination.stat().st_size,
                "build_provenance": provenance,
            })

        manifest = {
            "schema_version": 1,
            "project": "MeshLog firmware for BerksMesh",
            "version": version,
            "git_commit": commit.lower(),
            "source_date_epoch": epoch,
            "source_tree_clean": True,
            "created_at": datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z"),
            "release_status": "UNVALIDATED",
            "warning": "Development candidate only. Compilation does not establish physical-board or operational support.",
            "radio_profile": {"frequency_mhz": 869.618, "bandwidth_khz": 62.5, "spreading_factor": 8, "coding_rate": "4/8"},
            "files": files,
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        sums = "".join(f"{item['sha256']}  {item['filename']}\n" for item in files)
        sums += f"{sha256(manifest_path)}  manifest.json\n"
        (staging / "SHA256SUMS").write_text(sums, encoding="utf-8")
        staging.rename(output)
        return manifest
    finally:
        # Only remove the random temporary directory created by this invocation.
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=Path(".pio/build"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--source-date-epoch", required=True, type=int)
    args = parser.parse_args()
    package(
        args.build_root, args.output, args.version, args.commit,
        args.source_date_epoch, args.repo_root,
    )


if __name__ == "__main__":
    main()
