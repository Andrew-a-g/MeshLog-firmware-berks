#!/usr/bin/env python3
"""Publish only the exact owner-approved candidate bytes for v1.5.0-berks.5.

Path-dependent ELF build hashes make a CI rebuild differ from the approved
candidate even when executable sections and source timestamp match. This
one-release exception uses audited, Git-tracked candidate images instead.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.package_release import BOARDS, package, sha256
from scripts.verify_release_approval import verify

VERSION = "1.5.0-berks.5"


def package_approved(build_root: Path, approval_path: Path, output: Path) -> dict:
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approved = approval["approved_sha256_by_environment"]
    if set(approved) != {environment for _, _, environment in BOARDS}:
        raise ValueError("approval must cover exactly the eight supported boards")
    for _, _, environment in BOARDS:
        image = build_root / environment / "firmware-merged.bin"
        if not image.is_file() or sha256(image) != approved[environment]:
            raise ValueError(f"tracked candidate image does not match owner approval: {environment}")
    manifest = package(
        build_root, output, VERSION, approval["candidate_commit"],
        approval["candidate_source_date_epoch"], repo_root=None,
        release_status="VALIDATED",
    )
    verify(approval_path, output / "manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=Path("release-images/v1.5.0-berks.5"))
    parser.add_argument("--approval", type=Path, default=Path("docs/owner-validation-wsl-hf.json"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    package_approved(args.build_root, args.approval, args.output)
    print("Packaged exactly eight owner-approved images without rebuilding them")


if __name__ == "__main__":
    main()
