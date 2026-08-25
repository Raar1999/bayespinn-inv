"""What code did the interpreter actually load? (``PROV-07``)

The gap this closes
-------------------
``RunManifest`` records the git commit, the working-tree cleanliness and a tree
digest. All three describe **files on disk**. None of them describes the code the
interpreter actually imported, and those are not the same thing:

* an ignored ``build/`` directory holding a stale copy of the package -- this
  repository has one, ``build/lib/bayespinn_inv/``, gitignored and older than
  ``src/``, containing both ``inverse/identifiability.py`` and
  ``inverse/global_identifiability.py``;
* a leftover editable install pointing at a checkout that has since moved;
* a scratch directory earlier on ``sys.path`` than ``src/``.

In every case the manifest would report a clean tree at a known commit while the
published number came from code that commit does not contain. That is the
``PROV-02``/bifurcation pathology with a different entry point, and ``PKG-02``
(exec/import from a checkout path) is a second precedent in this repository.

The threat model is **accident, not attack**. Nobody has to hide anything: a
stale ``build/`` and a ``sys.path`` ordering are enough.

What the check does
-------------------
For every already-imported module belonging to ``package``, resolve its
``__file__`` and ask two questions:

1. does it lie inside the tracked tree?
2. if it does, is it a file git actually tracks?

Question 2 matters on its own -- a module inside the tree but untracked is
exactly the bifurcation, and question 1 alone would pass it.

The ``sys.path`` entries in effect are recorded alongside, because they are what
*would* decide the answer on the next import.

Platform assumptions, stated rather than assumed
------------------------------------------------
``PATH SEMANTICS``
    Comparison is done on ``Path.resolve()`` output, which follows symlinks,
    Windows junctions and substituted drives. A tracked file reached through a
    link that lands outside the tree is therefore reported **outside**. That is
    the deliberate choice: what matters is the bytes the interpreter read.

``CASE SENSITIVITY``
    ``D:\\Repo\\src`` and ``d:\\repo\\SRC`` are one file on NTFS and two on ext4.
    The check compares with :func:`os.path.normcase`, which case-folds on Windows
    and is the identity on POSIX, so it cannot raise a false "outside tree" on a
    case-insensitive filesystem. The assumption is also **probed** at run time
    rather than inferred from ``sys.platform``, because a case-sensitive
    directory on Windows and a case-insensitive mount on Linux both exist.

``EDITABLE-INSTALL LAYOUT``
    PEP 660 editable installs put either a ``.pth`` file or an
    ``__editable__*`` finder module on the path; the legacy ``pip install -e``
    used an egg-link. Any of them can point somewhere other than this checkout.
    Markers found on ``sys.path`` are recorded verbatim, not interpreted.

``VALIDATION``
    ``validated_on`` records the platform the positive control actually ran on.
    Every other platform is listed in ``unvalidated_platforms``. An unvalidated
    platform is stated, never assumed (generation-7 ruling, ``SPEC-g7-5``).

This module never raises. A provenance check that can crash a run is a provenance
check people switch off.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "loaded_code_provenance",
    "probe_case_sensitivity",
]

#: Repository root when the package is used from a source checkout.
_DEFAULT_REPO = Path(__file__).resolve().parents[3]


def probe_case_sensitivity(root: Path) -> Optional[bool]:
    """Is the filesystem holding ``root`` case-sensitive? ``None`` if unknown.

    Probed by asking whether an upper-cased spelling of an existing path names
    the same file. Creates nothing and writes nothing.
    """
    try:
        root = Path(root).resolve()
        if not root.exists():
            return None
        flipped = Path(str(root).upper())
        if str(flipped) == str(root):
            flipped = Path(str(root).lower())
        if str(flipped) == str(root):
            return None
        if not flipped.exists():
            return True                      # the other spelling is not a path
        return not os.path.samefile(str(root), str(flipped))
    except (OSError, ValueError):
        return None


def _tracked_files(root: Path) -> Optional[set]:
    """``git ls-files`` as a set of normcased absolute paths, or ``None``."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], capture_output=True,
                             timeout=30, cwd=str(root))
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    names = out.stdout.decode("utf-8", "replace").split("\0")
    return {os.path.normcase(str((root / n).resolve()))
            for n in names if n}


def _is_inside(child: str, parent: str) -> bool:
    """Containment on normcased resolved paths, without ``Path.is_relative_to``.

    ``is_relative_to`` arrived in 3.9; the string form keeps this module usable
    on the whole declared support range and makes the case rule explicit at the
    point of comparison.
    """
    c, p = os.path.normcase(child), os.path.normcase(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def loaded_code_provenance(package: str = "bayespinn_inv",
                           tree_root: Optional[Path] = None,
                           ) -> Dict[str, Any]:
    """Resolved ``__file__`` of every imported ``package`` module, versus the tree.

    Returns a dict safe to embed in a manifest. ``flagged`` is ``True`` when any
    imported module resolved outside the tracked tree **or** inside it but
    untracked -- either one means the manifest's commit does not describe the
    code that ran.
    """
    root = Path(tree_root) if tree_root is not None else _DEFAULT_REPO
    with contextlib.suppress(OSError):
        root = root.resolve()
    root_s = str(root)

    tracked = _tracked_files(root)
    modules: Dict[str, Dict[str, Any]] = {}
    outside: List[str] = []
    untracked: List[str] = []

    for name, mod in sorted(sys.modules.items()):
        if name != package and not name.startswith(package + "."):
            continue
        f = getattr(mod, "__file__", None)
        if not f:
            modules[name] = {"file": None, "inside_tree": None, "tracked": None,
                             "note": "namespace package or builtin"}
            continue
        try:
            rf = str(Path(f).resolve())
        except OSError:
            rf = str(f)
        inside = _is_inside(rf, root_s)
        is_tracked: Optional[bool] = None
        if tracked is not None and inside:
            is_tracked = os.path.normcase(rf) in tracked
        modules[name] = {"file": rf, "inside_tree": inside, "tracked": is_tracked}
        if not inside:
            outside.append(name)
        elif is_tracked is False:
            untracked.append(name)

    path_entries = []
    editable_markers = []
    for entry in sys.path:
        e = entry or "."
        try:
            re_ = str(Path(e).resolve())
        except OSError:
            re_ = e
        exists = os.path.exists(re_)
        path_entries.append({"entry": entry, "resolved": re_, "exists": exists,
                             "inside_tree": _is_inside(re_, root_s)})
        base = os.path.basename(re_)
        if base.startswith("__editable__") or base.endswith(".egg-link"):
            editable_markers.append(re_)
        if exists and os.path.isdir(re_):
            try:
                for child in os.listdir(re_):
                    if (child.startswith("__editable__")
                            or child.endswith(".egg-link")):
                        editable_markers.append(os.path.join(re_, child))
            except OSError:
                pass

    case_sensitive = probe_case_sensitivity(root)
    return {
        "package": package,
        "tree_root": root_s,
        "git_ls_files_available": tracked is not None,
        "n_modules_imported": len(modules),
        "modules": modules,
        "outside_tree": outside,
        "inside_tree_untracked": untracked,
        "flagged": bool(outside or untracked),
        "sys_path": path_entries,
        "editable_install_markers": sorted(set(editable_markers)),
        "platform_assumptions": {
            "os": sys.platform,
            "path_separator": os.sep,
            "resolution": ("Path.resolve(): follows symlinks, Windows junctions "
                           "and substituted drives; a module reached through a "
                           "link landing outside the tree is reported OUTSIDE"),
            "case_comparison": ("os.path.normcase -- case-folded on Windows, "
                                "identity on POSIX"),
            "filesystem_case_sensitive_probed": case_sensitive,
            "validated_on": (f"{sys.platform} / python "
                             f"{sys.version_info.major}.{sys.version_info.minor}"
                             f".{sys.version_info.micro}"),
            "unvalidated_platforms": [
                p for p in ("win32", "linux", "darwin") if p != sys.platform],
        },
    }
