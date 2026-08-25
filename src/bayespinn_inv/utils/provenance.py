"""
Run provenance: make every published number answer "what produced this?".

Each experiment writes a ``manifest.json`` next to its results containing the
git commit, the working-tree cleanliness, library versions, hardware, seeds and
the full configuration. Without this, a number in a results table is an
assertion; with it, the number is a claim someone can check.

Usage
-----
    from bayespinn_inv.utils.provenance import RunManifest

    man = RunManifest.create("identifiability", config={...}, seed=0)
    ...
    man.add_result("identifiable_rank", 4)
    man.write(out_dir)
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = ["RunManifest", "environment_info", "git_commit", "git_is_dirty"]


def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parents[3]),
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:
        return None


def git_commit() -> Optional[str]:
    """Full SHA of HEAD, or None outside a git checkout."""
    return _git("rev-parse", "HEAD")


def git_is_dirty() -> Optional[bool]:
    """True if tracked files differ from HEAD. None if git is unavailable.

    A result produced from a dirty tree is not reproducible from the commit
    alone, so this must be recorded rather than assumed clean.
    """
    status = _git("status", "--porcelain", "--untracked-files=no")
    if status is None:
        return None
    return bool(status.strip())


def environment_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    for mod in ("numpy", "scipy", "torch", "sklearn", "matplotlib"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            info[mod] = None
    try:
        import torch
        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_device"] = (torch.cuda.get_device_name(0)
                               if torch.cuda.is_available() else None)
        info["torch_threads"] = torch.get_num_threads()
    except Exception:
        pass
    return info


@dataclass
class RunManifest:
    """Machine-readable provenance record for one experiment."""

    experiment: str
    created_utc: str
    git_commit: Optional[str]
    git_dirty: Optional[bool]
    environment: Dict[str, Any]
    config: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None
    results: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def create(cls, experiment: str, config: Optional[Dict[str, Any]] = None,
               seed: Optional[int] = None, notes: str = "") -> "RunManifest":
        return cls(
            experiment=experiment,
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            git_commit=git_commit(),
            git_dirty=git_is_dirty(),
            environment=environment_info(),
            config=dict(config or {}),
            seed=seed,
            notes=notes,
        )

    def add_result(self, key: str, value: Any) -> None:
        self.results[key] = value

    def add_artifact(self, key: str, path) -> None:
        self.artifacts[key] = str(path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment": self.experiment,
            "created_utc": self.created_utc,
            "git": {"commit": self.git_commit, "dirty": self.git_dirty},
            "environment": self.environment,
            "seed": self.seed,
            "config": self.config,
            "results": self.results,
            "artifacts": self.artifacts,
            "notes": self.notes,
        }

    def write(self, out_dir) -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "manifest.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str),
                        encoding="utf-8")
        return path
