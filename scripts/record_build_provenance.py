"""PlatformIO pre-script: attest the exact clean source used by one build."""

Import("env")  # type: ignore[name-defined]  # supplied by PlatformIO/SCons

import json
import os
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=env.subst("$PROJECT_DIR"),  # type: ignore[name-defined]
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


epoch_text = os.environ.get("SOURCE_DATE_EPOCH")
if epoch_text is None or not epoch_text.isdecimal():
    raise RuntimeError("SOURCE_DATE_EPOCH must be set to a non-negative integer")

commit = git("rev-parse", "HEAD").lower()
if not __import__("re").fullmatch(r"[0-9a-f]{40}", commit):
    raise RuntimeError("could not determine the full Git HEAD")
if git("status", "--porcelain", "--untracked-files=all"):
    raise RuntimeError("release-oriented builds require a clean source tree")

provenance = {
    "schema_version": 1,
    "environment": env.subst("$PIOENV"),  # type: ignore[name-defined]
    "git_commit": commit,
    "source_date_epoch": int(epoch_text),
    "source_tree_clean": True,
}
build_dir = Path(env.subst("$BUILD_DIR"))  # type: ignore[name-defined]
build_dir.mkdir(parents=True, exist_ok=True)
(build_dir / "build-provenance.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
