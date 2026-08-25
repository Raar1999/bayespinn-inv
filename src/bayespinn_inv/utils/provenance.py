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

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "RunManifest",
    "environment_info",
    "git_commit",
    "git_is_dirty",
    "git_status_counts",
    "git_tree_digest",
]

#: Repository root when the package is used from a source checkout.
_DEFAULT_REPO = Path(__file__).resolve().parents[3]


def _git_bytes(*args: str, repo: Optional[Path] = None) -> Optional[bytes]:
    """Raw stdout of a git command, or ``None`` if git or the repo is unavailable."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True, timeout=30,
            cwd=str(repo if repo is not None else _DEFAULT_REPO),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _git(*args: str, repo: Optional[Path] = None) -> Optional[str]:
    raw = _git_bytes(*args, repo=repo)
    return None if raw is None else raw.decode("utf-8", "replace").strip()


def git_commit(repo: Optional[Path] = None) -> Optional[str]:
    """Full SHA of HEAD, or None outside a git checkout."""
    return _git("rev-parse", "HEAD", repo=repo)


def git_status_counts(repo: Optional[Path] = None) -> Optional[Dict[str, int]]:
    """Count the two *distinct* ways a tree can diverge from its commit.

    AUDIT_g0 PROV-02: a single boolean cannot distinguish "one line was edited"
    from "six source modules and 83% of the test suite are absent from this
    commit". Both make a result unreproducible from the commit, but only the
    second means the commit is a different program. They are counted separately
    so a reader of the manifest can tell which happened.

    Ignored files (build output, caches) are not divergence and are excluded.

    Returns
    -------
    dict or None
        ``{"tracked_modified": int, "untracked": int}``; ``None`` if git is
        unavailable or the path is not a checkout.
    """
    raw = _git_bytes("status", "--porcelain", "--untracked-files=all", "-z",
                     repo=repo)
    if raw is None:
        return None
    tracked = untracked = 0
    # -z output: "XY path\0" per entry, with an extra "\0origpath" after a rename.
    fields = raw.split(b"\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 3:
            continue
        code = entry[:2].decode("ascii", "replace")
        if code == "??":
            untracked += 1
        else:
            tracked += 1
            if "R" in code or "C" in code:
                i += 1        # consume the rename/copy source path
    return {"tracked_modified": tracked, "untracked": untracked}


def git_is_dirty(repo: Optional[Path] = None) -> Optional[bool]:
    """True if the working tree differs from HEAD in any way that matters.

    AUDIT_g0 PROV-02: this previously ran with ``--untracked-files=no``, so a
    tree missing entire source modules reported *clean*. Measured on a scratch
    repository, a tree with three untracked modules returned ``False``. That is
    the generation-0 state, in which 33 untracked paths carried 6 of 40 source
    modules and 204 of 246 tests.

    Untracked files now count, because a result produced by code that is not in
    the commit is exactly as unreproducible as one produced by edited code.
    Ignored files do not count -- regenerable build output is not divergence.

    Returns ``None`` if git is unavailable, so callers can tell "clean" from
    "unknown".
    """
    counts = git_status_counts(repo=repo)
    if counts is None:
        return None
    return bool(counts["tracked_modified"] or counts["untracked"])


def git_tree_digest(repo: Optional[Path] = None) -> Optional[str]:
    """SHA-256 over the content of every non-ignored file in the tree.

    Two runs can name the same commit and still have been produced by different
    code -- that is precisely what happened before the generation-0 adoption
    commit. The commit SHA cannot detect it and the dirty flag only says *that*
    something differs. This digest says *which* tree ran, so two manifests can be
    compared directly.

    Covers tracked files plus untracked-but-not-ignored files, hashed by content
    and keyed by path, so it is independent of file order and of mtime.
    """
    raw = _git_bytes("ls-files", "-c", "-o", "--exclude-standard", "-z", repo=repo)
    if raw is None:
        return None
    root = Path(repo if repo is not None else _DEFAULT_REPO)
    names = sorted(n.decode("utf-8", "replace") for n in raw.split(b"\0") if n)
    outer = hashlib.sha256()
    for name in names:
        path = root / name
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            digest = "absent"        # staged deletion, or a broken symlink
        outer.update(f"{digest}  {name}\n".encode("utf-8"))
    return outer.hexdigest()


def environment_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        # AUDIT_g6 §3.4. core.autocrlf was `true` at system level on the machine
        # that adopted this tree, which would have rewritten 119 CRLF files during
        # staging and broken the c115757 attestation. `.gitattributes` now pins
        # `* -text` so the setting cannot matter, but it is recorded anyway: if a
        # future result ever fails to reproduce, the first question is whether the
        # bytes on disk were the bytes in the commit, and this answers it without
        # requiring the tree that produced the result to still exist.
        "git_autocrlf": _git("config", "core.autocrlf"),
        "git_eol": _git("config", "core.eol"),
    }
    for mod in ("numpy", "scipy", "torch", "sklearn", "matplotlib"):
        try:
            m = __import__(mod)
        except ImportError:
            info[mod] = None          # not installed; None means "absent"
        else:
            info[mod] = getattr(m, "__version__", "unknown")

    # AUDIT_g0 SW-04a: this block was `except Exception: pass`, which SW-04
    # forbids in library code. Swallowing the error silently omitted the CUDA
    # keys from the manifest, so a reader could not tell "this run had no GPU"
    # from "the probe failed" -- and a provenance record whose absent fields are
    # ambiguous is the defect PROV-02 was about, in miniature. The keys are now
    # always present: None for absent, and the reason recorded when the probe
    # itself fails.
    info["cuda_available"] = None
    info["cuda_device"] = None
    info["torch_threads"] = None
    try:
        import torch
    except ImportError:
        info["torch_probe_error"] = "torch is not installed"
    else:
        try:
            available = bool(torch.cuda.is_available())
            info["cuda_available"] = available
            info["cuda_device"] = torch.cuda.get_device_name(0) if available else None
            info["torch_threads"] = torch.get_num_threads()
        except (RuntimeError, OSError, AssertionError) as exc:
            # A broken or partially-initialised CUDA driver raises here. Record
            # it rather than reporting the run as CPU-only.
            info["torch_probe_error"] = f"{type(exc).__name__}: {exc}"
    return info


@dataclass
class RunManifest:
    """Machine-readable provenance record for one experiment."""

    experiment: str
    created_utc: str
    git_commit: Optional[str]
    git_dirty: Optional[bool]
    environment: Dict[str, Any]
    #: AUDIT_g0 PROV-02: recorded separately so a reader can tell an edited line
    #: from a source module that is absent from the commit entirely.
    git_tracked_modified: Optional[int] = None
    git_untracked: Optional[int] = None
    #: Content digest of the tree that actually ran, independent of the commit.
    git_tree_digest: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None
    results: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def create(cls, experiment: str, config: Optional[Dict[str, Any]] = None,
               seed: Optional[int] = None, notes: str = "") -> "RunManifest":
        # One status call, so the flag and the counts can never disagree.
        counts = git_status_counts()
        dirty = (None if counts is None
                 else bool(counts["tracked_modified"] or counts["untracked"]))
        return cls(
            experiment=experiment,
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            git_commit=git_commit(),
            git_dirty=dirty,
            environment=environment_info(),
            git_tracked_modified=None if counts is None else counts["tracked_modified"],
            git_untracked=None if counts is None else counts["untracked"],
            git_tree_digest=git_tree_digest(),
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
            "git": {
                "commit": self.git_commit,
                "dirty": self.git_dirty,
                "tracked_modified": self.git_tracked_modified,
                "untracked": self.git_untracked,
                "tree_digest": self.git_tree_digest,
            },
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
