"""PROV-07: the manifest must see the code the interpreter actually loaded.

Every check here runs in a **subprocess**. A shadowing import cannot be undone
in-process -- once ``bayespinn_inv`` is in ``sys.modules`` the experiment is
over -- and a provenance test that leaves a poisoned interpreter behind would
contaminate every test that runs after it.

Controls, in the order the generation-7 ruling requires them:

* a **negative control** -- the ordinary source-checkout import, which must NOT
  be flagged, because a check that fires on the clean case is noise;
* a **planted shadow** outside the tree, the canonical positive control;
* the **live** ``build/lib/bayespinn_inv/`` copy, which is gitignored, stale, and
  already present in this repository -- the accidental case ``PROV-07`` is about,
  not a constructed one;
* an **in-tree untracked** module, which ``outside_tree`` alone would pass. This
  is the bifurcation shape (``PROV-02``), and it is the reason the check asks two
  questions instead of one.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "src" / "bayespinn_inv" / "utils" / "loaded_code.py"


def _run_probe(body: str) -> dict:
    """Execute ``body`` in a fresh interpreter and return the check's verdict.

    The checker is loaded from its absolute path under a private module name, so
    it cannot itself be shadowed by whatever the probe puts on ``sys.path``.
    """
    script = textwrap.dedent(f"""
        import importlib.util, json, sys
        spec = importlib.util.spec_from_file_location("_prov_check", r"{CHECKER}")
        _m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_m)
        ROOT = r"{ROOT}"
        {textwrap.indent(textwrap.dedent(body), "        ").strip()}
        print("@@@" + json.dumps(_m.loaded_code_provenance(tree_root=ROOT)))
    """)
    out = subprocess.run([sys.executable, "-c", script],
                         capture_output=True, timeout=180)
    text = out.stdout.decode("utf-8", "replace")
    assert "@@@" in text, (
        f"probe produced no verdict\nstdout: {text}\n"
        f"stderr: {out.stderr.decode('utf-8', 'replace')}")
    return json.loads(text.split("@@@", 1)[1].splitlines()[0])


def test_negative_control_clean_checkout_is_not_flagged():
    """The ordinary import must pass. A check that cries wolf gets disabled."""
    v = _run_probe(f"""
        sys.path.insert(0, r"{ROOT / 'src'}")
        import bayespinn_inv.inverse.identifiability
        import bayespinn_inv.utils.provenance
    """)
    assert v["flagged"] is False, (
        f"clean checkout flagged: outside={v['outside_tree']} "
        f"untracked={v['inside_tree_untracked']}")
    assert v["n_modules_imported"] >= 3
    assert v["git_ls_files_available"] is True
    ident = v["modules"]["bayespinn_inv.inverse.identifiability"]
    assert ident["inside_tree"] is True
    assert ident["tracked"] is True


def test_positive_control_planted_shadow_outside_tree(tmp_path):
    """Plant a package outside the tree, import from it, and confirm it fires."""
    shadow = tmp_path / "shadow"
    (shadow / "bayespinn_inv").mkdir(parents=True)
    (shadow / "bayespinn_inv" / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "bayespinn_inv" / "planted.py").write_text(
        "VALUE = 'this did not come from the tracked tree'\n", encoding="utf-8")

    v = _run_probe(f"""
        sys.path.insert(0, r"{shadow}")
        import bayespinn_inv.planted
    """)
    assert v["flagged"] is True, "planted shadow did not fire the check"
    assert "bayespinn_inv.planted" in v["outside_tree"]
    assert "bayespinn_inv" in v["outside_tree"]
    assert v["modules"]["bayespinn_inv.planted"]["inside_tree"] is False
    assert str(tmp_path) in v["modules"]["bayespinn_inv.planted"]["file"]


@pytest.mark.skipif(not (ROOT / "build" / "lib" / "bayespinn_inv").is_dir(),
                    reason="no build/lib copy present in this checkout")
def test_positive_control_live_build_lib_copy():
    """The gitignored ``build/lib`` copy is the accidental case, and it is real.

    ``build/`` is in ``.gitignore``, so ``git status`` is clean while it holds a
    stale duplicate of the identifiability modules. If it ever reaches
    ``sys.path`` first, the published number comes from code the recorded commit
    does not contain and nothing else in the manifest would say so.
    """
    v = _run_probe(f"""
        sys.path.insert(0, r"{ROOT / 'build' / 'lib'}")
        import bayespinn_inv.inverse.identifiability
    """)
    assert v["flagged"] is True, "the live build/lib shadow did not fire"
    flagged = set(v["outside_tree"]) | set(v["inside_tree_untracked"])
    assert "bayespinn_inv.inverse.identifiability" in flagged
    rec = v["modules"]["bayespinn_inv.inverse.identifiability"]
    assert "build" in rec["file"].replace("\\", "/").split("/")
    # Inside the repo directory but NOT tracked -- so `inside_tree` alone would
    # have passed it. This is exactly why the check asks about tracking too.
    assert rec["tracked"] is not True


def test_positive_control_in_tree_untracked_module():
    """A module inside the tree but untracked by git: the bifurcation shape."""
    probe = ROOT / "src" / "bayespinn_inv" / "_g7_untracked_probe.py"
    if probe.exists():
        pytest.skip("probe path already occupied; refusing to overwrite")
    probe.write_text("VALUE = 'untracked but in-tree'\n", encoding="utf-8")
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(probe)],
            capture_output=True, cwd=str(ROOT), timeout=30)
        assert tracked.returncode != 0, "the probe file is tracked; test invalid"

        v = _run_probe(f"""
            sys.path.insert(0, r"{ROOT / 'src'}")
            import bayespinn_inv._g7_untracked_probe
        """)
    finally:
        probe.unlink()

    assert v["flagged"] is True, "an untracked in-tree module did not fire"
    assert "bayespinn_inv._g7_untracked_probe" in v["inside_tree_untracked"]
    rec = v["modules"]["bayespinn_inv._g7_untracked_probe"]
    assert rec["inside_tree"] is True and rec["tracked"] is False


def test_platform_assumptions_are_stated_not_assumed():
    """SPEC-g7-5: the platform block must say what was validated and what was not."""
    v = _run_probe(f"""
        sys.path.insert(0, r"{ROOT / 'src'}")
        import bayespinn_inv.utils.provenance
    """)
    pa = v["platform_assumptions"]
    assert pa["validated_on"].startswith(sys.platform)
    assert sys.platform not in pa["unvalidated_platforms"]
    assert set(pa["unvalidated_platforms"]) <= {"win32", "linux", "darwin"}
    assert pa["unvalidated_platforms"], "no platform marked unvalidated"
    # Probed, not inferred from sys.platform.
    assert pa["filesystem_case_sensitive_probed"] in (True, False, None)
    for key in ("case_comparison", "resolution", "path_separator"):
        assert pa[key]


def test_manifest_carries_the_check(tmp_path):
    """The mitigation is only real if RunManifest actually writes it.

    This asserts the *mechanism*, not that today's working tree happens to be
    clean. Pinning ``flagged is False`` here would make the test fail during any
    generation that adds a module before committing it -- which is precisely the
    state the check is supposed to report, not a state the suite should forbid.
    What is pinned instead is self-consistency: every module the check calls
    untracked must actually be untracked according to git.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from bayespinn_inv.utils.provenance import RunManifest

    man = RunManifest.create("prov07_selftest", config={}, seed=0)
    path = man.write(tmp_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert "loaded_code" in doc, "manifest does not record the loaded code"
    lc = doc["loaded_code"]
    assert lc["package"] == "bayespinn_inv"
    assert lc["sys_path"], "sys.path not recorded"
    assert isinstance(lc["flagged"], bool)
    assert lc["flagged"] == bool(lc["outside_tree"] or lc["inside_tree_untracked"])

    for name in lc["inside_tree_untracked"]:
        f = lc["modules"][name]["file"]
        r = subprocess.run(["git", "ls-files", "--error-unmatch", f],
                           capture_output=True, cwd=str(ROOT), timeout=30)
        assert r.returncode != 0, (
            f"{name} was reported untracked but git tracks {f}")
    for name in lc["outside_tree"]:
        f = lc["modules"][name]["file"]
        assert not f.lower().startswith(str(ROOT).lower()), (
            f"{name} was reported outside the tree but {f} is inside it")
