"""Synthetic source fixtures only; never manufacture human pilot answers."""
import copy
import base64
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from proquest_tdm_review import (CHOICES, COMPARISONS, ReviewStore, launch, load_pack,
                                recover, sha, source_html)


class TDMReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data/verified").mkdir(parents=True)
        (self.root / "data/raw").mkdir()
        self.rows = [dict(page_id="123", date="1975-01-01", topic="production", quote=q,
                          verify_reason="HIDDEN VERIFIER") for q in ("First forecast.", "Second forecast.")]
        self.verified = self.root / "data/verified/pred_proquest_economy_1975.jsonl"
        self.raw = self.root / "data/raw/proquest_economy_1975.jsonl"
        self.verified.write_text("\n" + "\n\n".join(json.dumps(r) for r in self.rows) + "\n")
        self.raw.write_text(json.dumps(dict(page_id="123", date="1975-01-01",
                                           ocr_text="First forecast. Second forecast.")) + "\n")
        stripped = "".join(json.dumps({k: v for k, v in r.items() if k != "quote"}) + "\n" for r in self.rows)
        self.record = dict(audit_id="verified:1975:2", page_id="123", date="1975-01-01", publisher="Synthetic",
                           source_path="data/proquest/verified/pred_proquest_economy_1975.export.jsonl",
                           source_line="2", source_sha256=sha(stripped.encode()))
        self.comparison = self.root / "comparison.json"
        self.comparison.write_text(json.dumps({"records": [dict(audit_id=self.record["audit_id"], topic="production")]}))
        self.pack = dict(pack_id="fixture", rubric="fixture", records=[self.record],
                         comparison_sha256=sha(self.comparison.read_bytes()))

    def test_ordinal_lineage_keeps_duplicate_labels_and_physical_location(self):
        result = recover(self.root, self.record)
        self.assertTrue(result["recovered"])
        self.assertEqual(result["quote"], "Second forecast.")
        self.assertIn(":4;", result["locator"])
        self.assertEqual(result["quote_occurrences"], 1)
        rendered = source_html(self.record, result)
        self.assertIn("<mark>Second forecast.</mark>", rendered)
        self.assertNotIn("HIDDEN VERIFIER", rendered)
        self.assertNotIn("production", rendered)

    def test_hash_mismatch_never_falls_back_to_label_match(self):
        with self.verified.open("a") as handle:
            handle.write(json.dumps(self.rows[0]) + "\n")
        result = recover(self.root, self.record)
        self.assertFalse(result["recovered"])
        self.assertEqual(result["quote"], "")
        self.assertIn("hash", result["reason"])

    def test_missing_duplicate_and_wrong_article_are_retained(self):
        original = self.raw.read_text()
        for content, status in [("", "unavailable"), (original*2, "ambiguous"),
                                (original.replace("1975-01-01", "1975-01-02"), "wrong_article")]:
            with self.subTest(status=status):
                self.raw.write_text(content)
                result = recover(self.root, self.record)
                self.assertFalse(result["recovered"])
                self.assertEqual(result["status"], status)
                self.assertEqual(result["audit_id"], self.record["audit_id"])

    def first_pass(self):
        return {"reviewer": "Synthetic test", "answers": dict({k: v[-1] for k, v in CHOICES.items()},
                mapping_status="unique", initial_note="Synthetic fixture", quantity="unclear", attribution="unclear"),
                "provenance": {"recovered": True}}

    def test_blinding_lock_resume_and_append_only_comparisons(self):
        store = ReviewStore(self.root / "responses", self.pack)
        aid = self.record["audit_id"]
        with self.assertRaisesRegex(ValueError, "locked"):
            store.comparison(aid, self.comparison)
        store.record(aid, "first_pass", self.first_pass())
        before = copy.deepcopy(store.events(aid, "first_pass"))
        for kind in ("draft", "first_pass"):
            with self.assertRaisesRegex(ValueError, "locked"):
                store.record(aid, kind, self.first_pass())
        with self.assertRaisesRegex(ValueError, "Reveal"):
            store.record(aid, "comparison", {})
        self.assertEqual(store.comparison(aid, self.comparison)["topic"], "production")
        store.record(aid, "comparison", {k: v[-1] for k, v in COMPARISONS.items()})
        store.record(aid, "correction", {"note": "Synthetic correction"})
        resumed = ReviewStore(self.root / "responses", self.pack)
        self.assertEqual(before, resumed.events(aid, "first_pass"))
        self.assertEqual(len(resumed.events(aid)), 4)

    def test_missing_answers_and_unknown_ids_rejected(self):
        store = ReviewStore(self.root, self.pack)
        aid = self.record["audit_id"]
        with self.assertRaisesRegex(ValueError, "Unknown"):
            store.record("different", "draft", {})
        value = self.first_pass()
        value["answers"]["direction"] = ""
        with self.assertRaisesRegex(ValueError, "direction"):
            store.record(aid, "first_pass", value)
        value = self.first_pass()
        value["provenance"] = {}
        with self.assertRaisesRegex(ValueError, "lineage"):
            store.record(aid, "first_pass", value)

    def test_unavailable_requires_only_mapping_blinding_note_and_cannot_reveal(self):
        store = ReviewStore(self.root, self.pack)
        aid = self.record["audit_id"]
        store.record(aid, "first_pass", {"reviewer": "Synthetic test", "answers": {
            "mapping_status": "unavailable", "blinding": "uncertain", "initial_note": "No article"}})
        with self.assertRaisesRegex(ValueError, "unassessable"):
            store.comparison(aid, self.comparison)

    def test_concurrent_session_cannot_overwrite_and_bad_comparison_cannot_reveal(self):
        a, b = ReviewStore(self.root, self.pack), ReviewStore(self.root, self.pack)
        aid = self.record["audit_id"]
        a.record(aid, "first_pass", self.first_pass())
        with self.assertRaisesRegex(ValueError, "Another review"):
            b.record(aid, "draft", {})
        self.comparison.write_text("{}")
        with self.assertRaisesRegex(ValueError, "changed"):
            a.comparison(aid, self.comparison)
        self.assertFalse(a.events(aid, "reveal"))

    def test_real_pack_remains_frozen_and_notebook_has_no_answers(self):
        pack = load_pack(ROOT / "data/scored/proquest/source_review_pilot_v1/pack.json")
        self.assertEqual(len(pack["records"]), 12)
        notebook = json.loads((ROOT / "validation/proquest_review/ProQuest_Source_Review.ipynb").read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
                compile("".join(cell["source"]), "notebook", "exec")

    def test_offline_widgets_are_isolated_and_reject_unsafe_or_changed_files(self):
        source = (ROOT / "validation/proquest_review/offline_widgets.py").read_text()

        def payload(entries):
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                for name, content in entries.items():
                    archive.writestr(name, content)
            raw = data.getvalue()
            return {"synthetic.whl": {"sha256": sha(raw), "base64": base64.b64encode(raw).decode()}}

        entries = {"synthetic.py": "SYNTHETIC = True\n",
                   "jupyterlab_widgets-0.data/data/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager/package.json": "{}"}
        bundle = self.root / "isolated"
        bundle.mkdir()
        fake = types.SimpleNamespace(__version__="SYNTHETIC")
        def install(wheels):
            original_path = list(sys.path)
            try:
                with patch.object(Path, "home", return_value=self.root / "fake_home"), \
                     patch.dict(sys.modules, {"ipywidgets": fake}), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(source, "offline_widgets.py", "exec"), {"BUNDLE": bundle, "WHEELS": wheels})
            finally:
                sys.path[:] = original_path
        install(payload(entries))
        install(payload(entries))
        self.assertTrue((bundle / "widget_vendor/synthetic.py").exists())
        self.assertTrue((self.root / "fake_home/.local/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager/package.json").exists())
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            install(payload({"../outside.py": "bad"}))
        with self.assertRaisesRegex(ValueError, "Different existing"):
            install(payload({"synthetic.py": "changed"}))

    @unittest.skipUnless(importlib.util.find_spec("ipywidgets"), "Optional workbench widget dependency")
    def test_widget_save_reveal_compare_and_resume_with_synthetic_source(self):
        import ipywidgets as w
        unsigned = {k: v for k, v in self.pack.items() if k != "pack_id"}
        self.pack["pack_id"] = sha(json.dumps(unsigned, sort_keys=True).encode())
        (self.root / "pack.json").write_text(json.dumps(self.pack))

        def descendants(widget):
            yield widget
            for child in getattr(widget, "children", ()):
                yield from descendants(child)

        with patch("IPython.display.display") as display:
            store = launch(self.root, self.root)
            ui = display.call_args.args[0]

        def button(label):
            return next(x for x in descendants(ui) if isinstance(x, w.Button) and x.description == label)

        self.assertTrue(button("Reveal machine labels").disabled)
        widgets = list(descendants(ui))
        next(x for x in widgets if isinstance(x, w.Text)).value = "Synthetic tester"
        for x in widgets:
            if isinstance(x, w.Dropdown):
                x.value = x.options[1][1]
            if isinstance(x, w.Textarea):
                x.value = "Synthetic test only"
        button("Save & lock first pass").click()
        aid = self.record["audit_id"]
        self.assertEqual(len(store.events(aid, "first_pass")), 1)
        self.assertFalse(button("Reveal machine labels").disabled)
        button("Reveal machine labels").click()
        self.assertEqual(len(store.events(aid, "reveal")), 1)
        for x in descendants(ui):
            if isinstance(x, w.Dropdown) and not x.disabled:
                x.value = x.options[-1][1]
        button("Save comparison").click()
        self.assertEqual(len(store.events(aid, "comparison")), 1)
        with patch("IPython.display.display"):
            resumed = launch(self.root, self.root)
        self.assertEqual(store.events(aid, "first_pass"), resumed.events(aid, "first_pass"))


if __name__ == "__main__":
    unittest.main()
