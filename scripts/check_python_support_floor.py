"""Is the declared ``requires-python`` floor supportable by this source tree?

Why this exists
---------------
``pyproject.toml`` declares ``requires-python = ">=3.9"`` and classifiers for
3.9 through 3.12. Generation 6 recorded that the CI matrix which was supposed to
evidence that claim **has never executed**, and generation 7 found that no 3.9 or
3.12 interpreter is obtainable on the development host either (``SK-09`` forbids
the network access that fetching one would need).

An unexecuted support claim is the ``S-4`` pattern: an API surface the project
advertises and has never run. This script is the strongest evidence obtainable
without the interpreter. It does not replace a green CI leg and does not claim
to -- it can only **falsify** the floor, never confirm it. Read its clean verdict
as "no obstruction found by this method", never as "3.9 works".

Two independent checks
----------------------
``syntax``
    Every source file is parsed by CPython's own parser restricted to the target
    grammar via ``ast.parse(..., feature_version=...)``. This executes; it is a
    measurement, not a judgement. It catches ``match`` (3.10), ``except*``
    (3.11), and anything else the grammar gained after the floor.

``api``
    An **AST** walk for standard-library and typing names that did not exist at
    the floor. ``SW-20``: a guard whose subject is source code is implemented
    over the AST, never over characters -- a character scan for ``tomllib``
    matches this sentence, and the four-instance defect class of generation 6 was
    exactly that mistake.

What neither check can see
--------------------------
Dependency *resolution*. ``numpy>=1.22`` admits 3.9, but on 3.9 pip resolves to
whatever the last 3.9-compatible release was, and whether the suite passes
against those versions is not decidable from this tree. Only the CI leg answers
that, which is why ``CI-01`` stays open regardless of what this script prints.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

#: Names introduced after 3.9, as (module, attribute) -> first version.
#: Attribute ``None`` means the whole module is new.
_NEW_API: Dict[Tuple[str, Optional[str]], Tuple[int, int]] = {
    ("tomllib", None): (3, 11),
    ("graphlib", None): (3, 9),
    ("itertools", "pairwise"): (3, 10),
    ("itertools", "batched"): (3, 12),
    ("math", "cbrt"): (3, 11),
    ("math", "exp2"): (3, 11),
    ("hashlib", "file_digest"): (3, 11),
    ("contextlib", "chdir"): (3, 11),
    ("contextlib", "aclosing"): (3, 10),
    ("asyncio", "TaskGroup"): (3, 11),
    ("asyncio", "timeout"): (3, 11),
    ("enum", "StrEnum"): (3, 11),
    ("enum", "ReprEnum"): (3, 11),
    ("types", "UnionType"): (3, 10),
    ("types", "EllipsisType"): (3, 10),
    ("dataclasses", "KW_ONLY"): (3, 10),
    ("typing", "Self"): (3, 11),
    ("typing", "Never"): (3, 11),
    ("typing", "LiteralString"): (3, 11),
    ("typing", "assert_never"): (3, 11),
    ("typing", "assert_type"): (3, 11),
    ("typing", "reveal_type"): (3, 11),
    ("typing", "dataclass_transform"): (3, 11),
    ("typing", "override"): (3, 12),
    ("typing", "TypeAlias"): (3, 10),
    ("typing", "ParamSpec"): (3, 10),
    ("typing", "Concatenate"): (3, 10),
    ("typing", "TypeGuard"): (3, 10),
    ("typing", "is_typeddict"): (3, 10),
    ("inspect", "get_annotations"): (3, 10),
    ("sys", "monitoring"): (3, 12),
    ("pathlib", "UnsupportedOperation"): (3, 13),
}

#: Keyword arguments that did not exist at 3.9, as (callee, keyword) -> version.
_NEW_KWARGS: Dict[Tuple[str, str], Tuple[int, int]] = {
    ("zip", "strict"): (3, 10),
    ("dataclass", "slots"): (3, 10),
    ("dataclass", "kw_only"): (3, 10),
    ("dataclass", "match_args"): (3, 10),
    ("dataclass", "weakref_slot"): (3, 11),
    ("anext", "default"): (3, 10),
}

#: Methods that did not exist at 3.9 and are distinctive enough to flag by name.
_NEW_METHODS: Dict[str, Tuple[int, int]] = {
    "bit_count": (3, 10),
    "batched": (3, 12),
    "getdoc": (3, 0),          # deliberately old: exercises the version filter
}


class _ApiVisitor(ast.NodeVisitor):
    """Collects uses of names newer than ``floor``.

    Tracks which modules were imported under which local name, so that
    ``import itertools as it; it.pairwise(...)`` is caught and an unrelated
    ``foo.pairwise(...)`` is not.
    """

    def __init__(self, floor: Tuple[int, int], path: str) -> None:
        self.floor = floor
        self.path = path
        self.findings: List[dict] = []
        self._alias_to_module: Dict[str, str] = {}
        self._imported_names: Dict[str, Tuple[str, str]] = {}

    def _flag(self, node, what: str, since: Tuple[int, int]) -> None:
        if since <= self.floor:
            return
        self.findings.append({
            "file": self.path,
            "line": getattr(node, "lineno", None),
            "name": what,
            "since": f"{since[0]}.{since[1]}",
        })

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            local = a.asname or a.name.split(".")[0]
            self._alias_to_module[local] = a.name
            if (a.name, None) in _NEW_API:
                self._flag(node, a.name, _NEW_API[(a.name, None)])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        if (mod, None) in _NEW_API:
            self._flag(node, mod, _NEW_API[(mod, None)])
        for a in node.names:
            key = (mod, a.name)
            if key in _NEW_API:
                self._flag(node, f"{mod}.{a.name}", _NEW_API[key])
            self._imported_names[a.asname or a.name] = (mod, a.name)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            mod = self._alias_to_module.get(node.value.id)
            if mod is not None and (mod, node.attr) in _NEW_API:
                self._flag(node, f"{mod}.{node.attr}", _NEW_API[(mod, node.attr)])

        if node.attr in _NEW_METHODS:
            self._flag(node, f".{node.attr}()", _NEW_METHODS[node.attr])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee = node.func.attr
        if callee is not None:
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                key = (callee, kw.arg)
                if key in _NEW_KWARGS:
                    self._flag(node, f"{callee}({kw.arg}=...)", _NEW_KWARGS[key])
        self.generic_visit(node)


def _has_future_annotations(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if (isinstance(node, ast.ImportFrom) and node.module == "__future__"
                and any(a.name == "annotations" for a in node.names)):
            return True
    return False


def _runtime_pep604(tree: ast.AST, path: str) -> List[dict]:
    """``X | Y`` in an annotation, in a file without ``from __future__ import annotations``.

    PEP 604 unions are 3.10+ at *runtime*. With the future import, annotations
    are strings and never evaluated, so 3.9 is fine; without it, the union is
    built at class/def creation time and 3.9 raises ``TypeError``.
    """
    if _has_future_annotations(tree):
        return []
    out: List[dict] = []

    def scan(ann, where):
        for n in ast.walk(ann):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                out.append({"file": path, "line": n.lineno,
                            "name": f"PEP 604 union in {where}", "since": "3.10"})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                if a.annotation is not None:
                    scan(a.annotation, "parameter annotation")
            if node.returns is not None:
                scan(node.returns, "return annotation")
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            scan(node.annotation, "variable annotation")
    return out


def check_tree(roots: List[Path], floor: Tuple[int, int],
               exclude: List[Path]) -> dict:
    ex = [e.resolve() for e in exclude]
    files: List[Path] = []
    for r in roots:
        for p in sorted(r.rglob("*.py")):
            rp = p.resolve()
            if any(str(rp).startswith(str(e)) for e in ex):
                continue
            if "__pycache__" in p.parts or "build" in p.parts:
                continue
            files.append(p)

    syntax: List[dict] = []
    api: List[dict] = []
    pep604: List[dict] = []
    for p in files:
        src = p.read_text(encoding="utf-8")
        try:
            ast.parse(src, filename=str(p), feature_version=floor)
        except SyntaxError as exc:
            syntax.append({"file": str(p), "line": exc.lineno,
                           "error": str(exc).split("(")[0].strip()})
            continue
        tree = ast.parse(src, filename=str(p))
        v = _ApiVisitor(floor, str(p))
        v.visit(tree)
        api.extend(v.findings)
        pep604.extend(_runtime_pep604(tree, str(p)))

    return {
        "floor": f"{floor[0]}.{floor[1]}",
        "n_files": len(files),
        "excluded": [str(e) for e in ex],
        "syntax_rejections": syntax,
        "api_uses_newer_than_floor": api,
        "runtime_pep604_unions": pep604,
        "obstruction_found": bool(syntax or api or pep604),
        "verdict_meaning": (
            "This method can only FALSIFY the floor. A clean result means 'no "
            "obstruction found by static analysis', never 'the floor works'. "
            "Dependency resolution at the floor is invisible here and only a CI "
            "leg can settle it."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--floor", default="3.9")
    ap.add_argument("--roots", default="src,tests,scripts")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    major, minor = (int(x) for x in args.floor.split("."))
    roots = [root / r for r in args.roots.split(",")]
    # SW-20: a guard whose subject is source code excludes its own source and
    # the prose describing it. This file lists the very names it searches for.
    exclude = [Path(__file__).resolve(),
               root / "tests" / "test_python_support_floor_g7.py"]

    report = check_tree(roots, (major, minor), exclude)
    print(f"floor {report['floor']}  files {report['n_files']}")
    print(f"  syntax rejections           : {len(report['syntax_rejections'])}")
    print(f"  API uses newer than floor   : {len(report['api_uses_newer_than_floor'])}")
    print(f"  runtime PEP 604 unions      : {len(report['runtime_pep604_unions'])}")
    for group in ("syntax_rejections", "api_uses_newer_than_floor",
                  "runtime_pep604_unions"):
        for f in report[group][:40]:
            print(f"    {f}")
    print(f"  obstruction found           : {report['obstruction_found']}")
    print(f"  {report['verdict_meaning']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  wrote {args.json}")
    return 1 if report["obstruction_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
