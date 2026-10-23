#!/usr/bin/env python3
"""Refuse a tagged release if its rebuilt bytes differ from owner-approved images."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.package_release import BOARDS, sha256


def verify(approval_path: Path, manifest_path: Path) -> None:
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved = approval["approved_sha256_by_environment"]
    environments = {environment for _, _, environment in BOARDS}
    if set(approved) != environments:
        raise ValueError("owner approval must contain exactly the release board matrix")
    if manifest["release_status"] != "VALIDATED":
        raise ValueError("tagged release manifest must be marked VALIDATED")
    files = manifest["files"]
    if len(files) != len(environments) or {item["environment"] for item in files} != environments:
        raise ValueError("release manifest does not contain each board exactly once")
    for item in files:
        environment = item["environment"]
        if item["sha256"] != approved[environment]:
            raise ValueError(f"rebuilt image differs from owner-approved bytes: {environment}")
        image = manifest_path.parent / item["filename"]
        if not image.is_file() or sha256(image) != approved[environment]:
            raise ValueError(f"image does not match owner-approved bytes: {environment}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    verify(args.approval, args.manifest)
    print("All eight release images match the owner-approved SHA-256 checksums")


if __name__ == "__main__":
    main()
