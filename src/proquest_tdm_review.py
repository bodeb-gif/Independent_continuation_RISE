"""Human source review inside TDM Jupyter. Source prose and responses stay on VM.

No network, model calls, resampling, or economic outcomes. Core uses stdlib;
launch() imports the workbench's ipywidgets only when displaying the interface.
"""
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile


CHOICES = {
    "mapping_status": ("unique", "ambiguous", "unavailable", "wrong_article"),
    "blinding": ("no_prior_label_exposure", "prior_label_exposure", "uncertain"),
    "is_forecast": ("yes", "no", "unclear"),
    "change_type": ("level", "growth_rate", "event_occurrence", "other", "unclear"),
    "direction": ("rise", "fall", "unchanged", "unclear"),
    "scope": ("US_national", "regional", "foreign", "firm_asset", "unclear"),
    "horizon_support": ("explicit", "inferable", "absent", "unclear"),
    "condition": ("unconditional", "conditional", "unclear"),
}
TEXT_FIELDS = ("quantity", "horizon_wording", "target_start", "target_end",
               "condition_text", "attribution", "original_forecast_date", "initial_note")
GRADES = ("correct", "incorrect", "unclear", "not_assessable")
COMPARISONS = {k: GRADES for k in ("topic", "direction", "scope", "confidence",
                                    "voice", "horizon_months", "horizon_hint")}
COMPARISONS.update(benchmark=("direct", "proxy", "mismatch", "unclear"),
                   joint_usability=("yes", "no", "unclear"),
                   error_category=("none", "not_forecast", "quantity", "direction",
                                   "scope", "horizon", "condition", "attribution",
                                   "mapping", "multiple", "other", "unclear"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def load_pack(path):
    pack = json.loads(Path(path).read_text())
    unsigned = {k: v for k, v in pack.items() if k != "pack_id"}
    if sha(json.dumps(unsigned, sort_keys=True).encode()) != pack["pack_id"]:
        raise ValueError("Changed pilot pack")
    ids = [r["audit_id"] for r in pack["records"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate audit IDs")
    return pack


def recover(project, record):
    """Prove export lineage by reconstructing strip_for_export.py's bytes.

    Only quote/claim_text were stripped. Nonblank record order is preserved;
    identical stripped labels are deliberately never used as matching keys.
    Read snapshots once so a running writer cannot silently change the hash.
    """
    project = Path(project)
    name = Path(record["source_path"]).name
    match = re.fullmatch(r"pred_proquest_economy_(\d{4})\.export\.jsonl", name)
    if not match or not 1900 <= int(match[1]) <= 2010:
        raise ValueError("Not an annual historical ProQuest shard")
    result = {"audit_id": record["audit_id"], "recovered": False, "quote": "",
              "article": "", "status": "unavailable", "reason": "", "locator": ""}
    verified = project / "data/verified" / name.replace(".export", "")
    raw = project / "data/raw" / f"proquest_economy_{match[1]}.jsonl"
    try:
        content = verified.read_bytes()
        stripped = hashlib.sha256()
        selected = None
        ordinal = 0
        for physical, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            ordinal += 1
            export = {k: v for k, v in row.items() if k not in {"quote", "claim_text"}}
            stripped.update((json.dumps(export) + "\n").encode())
            if ordinal == int(record["source_line"]):
                selected = (row, physical)
        if stripped.hexdigest() != record["source_sha256"]:
            raise ValueError("VM export reconstruction differs from frozen pilot hash; no label matching attempted")
        if selected is None:
            raise ValueError("Export row missing")
        row, physical = selected
        if str(row.get("page_id")) != str(record["page_id"]) or row.get("date") != record["date"]:
            raise ValueError("Article ID/date differs from pilot")
        result.update(locator=f"{verified}:{physical}; export ordinal {record['source_line']}",
                      verified_sha256=sha(content), export_sha256=stripped.hexdigest())
        quote = row.get("quote") or row.get("claim_text")
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError("Original claim has no quote")
        result["quote"] = quote
        # Annual article shards can be large; retain only matching articles.
        raw_hash, matches, match_count = hashlib.sha256(), [], 0
        before = raw.stat()
        with raw.open("rb") as handle:
            for n, line in enumerate(handle, 1):
                raw_hash.update(line)
                if not line.strip():
                    continue
                article = json.loads(line)
                if str(article.get("page_id")) == str(record["page_id"]):
                    match_count += 1
                    if len(matches) < 2:
                        matches.append((n, article))
        after = raw.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("Article shard changed during retrieval; reopen after its writer finishes")
        if match_count != 1:
            result["status"] = "ambiguous" if matches else "unavailable"
            raise ValueError(f"Expected one raw article; found {match_count}")
        raw_line, article = matches[0]
        if article.get("date") != record["date"]:
            result["status"] = "wrong_article"
            raise ValueError("Raw article date differs from pilot")
        text = article.get("ocr_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Article text unavailable")
        result.update(recovered=True, article=text, raw_sha256=raw_hash.hexdigest(),
                      raw_locator=f"{raw}:{raw_line}", status="lineage_recovered",
                      quote_occurrences=text.count(quote),
                      reason="Ordered export lineage recovered. Human must judge passage mapping.")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result["reason"] = str(exc)
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".review-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class ReviewStore:
    """One append-only event stream, with locked first passes and revision checks."""
    def __init__(self, directory, pack):
        self.path = Path(directory) / "human_review.json"
        self.pack = pack
        self.ids = {r["audit_id"] for r in pack["records"]}
        self.data = self._read()
        if self.data["pack_id"] != pack["pack_id"]:
            raise ValueError("Responses belong to a different pilot")

    def _read(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"schema": "proquest-tdm-human-v1", "pack_id": self.pack["pack_id"],
                "rubric": self.pack["rubric"], "revision": 0, "events": []}

    def events(self, audit_id, kind=None):
        return [e for e in self.data["events"] if e["audit_id"] == audit_id
                and (kind is None or e["kind"] == kind)]

    def record(self, audit_id, kind, value):
        import fcntl  # macOS/Linux; TDM uses Linux
        if audit_id not in self.ids:
            raise ValueError("Unknown pilot ID")
        locked = bool(self.events(audit_id, "first_pass"))
        if kind in {"draft", "first_pass"} and locked:
            raise ValueError("First pass is locked; append a correction note instead")
        if kind in {"reveal", "comparison", "comparison_draft", "correction"} and not locked:
            raise ValueError("Save and lock first pass before revealing or comparing")
        if kind in {"comparison", "comparison_draft"} and not self.events(audit_id, "reveal"):
            raise ValueError("Reveal labels before recording comparison")
        if kind not in {"draft", "first_pass", "reveal", "comparison", "comparison_draft", "correction"}:
            raise ValueError("Unknown event")
        if kind == "first_pass":
            answers = value["answers"]
            validate_choices(answers, {k: CHOICES[k] for k in ("mapping_status", "blinding")})
            if answers["mapping_status"] == "unique":
                validate_choices(answers, CHOICES)
            if not value.get("reviewer", "").strip() or not answers.get("initial_note", "").strip():
                raise ValueError("Reviewer and a brief evidence/mapping note are required")
            if answers["mapping_status"] == "unique" and not value.get("provenance", {}).get("recovered"):
                raise ValueError("Unique mapping requires recovered source lineage and article")
            if answers["mapping_status"] == "unique" and answers["is_forecast"] == "yes":
                if not answers.get("quantity", "").strip() or not answers.get("attribution", "").strip():
                    raise ValueError("Enter the predicted quantity and attribution (or unclear)")
        if kind == "comparison":
            validate_choices(value, COMPARISONS)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with (self.path.parent / ".review.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            disk = self._read()
            if disk["revision"] != self.data["revision"]:
                raise ValueError("Another review session saved changes. Reopen this notebook before continuing.")
            updated = copy.deepcopy(self.data)
            updated["events"].append({"audit_id": audit_id, "kind": kind,
                                      "saved_at": now(), "value": copy.deepcopy(value)})
            updated["revision"] += 1
            atomic_json(self.path, updated)
            self.data = updated

    def comparison(self, audit_id, path):
        if not self.events(audit_id, "first_pass"):
            raise ValueError("First pass must be locked")
        if self.events(audit_id, "first_pass")[0]["value"]["answers"]["mapping_status"] != "unique":
            raise ValueError("Unresolved mapping is retained as unassessable; comparison remains hidden")
        data = Path(path).read_bytes()
        if sha(data) != self.pack["comparison_sha256"]:
            raise ValueError("Comparison file changed")
        rows = json.loads(data)["records"]
        if len(rows) != len(self.ids) or {r["audit_id"] for r in rows} != self.ids:
            raise ValueError("Comparison IDs differ from pilot")
        self.record(audit_id, "reveal", {})
        return next(r for r in rows if r["audit_id"] == audit_id)


def validate_choices(answers, choices):
    for name, options in choices.items():
        if answers.get(name) not in options:
            raise ValueError(f"Please answer {name.replace('_', ' ')}")


def source_html(record, source):
    esc = html.escape
    quote, text = source["quote"], source["article"]
    pos = text.find(quote) if quote else -1
    if pos >= 0:
        context = (esc(text[max(0, pos-700):pos]) + "<mark>" + esc(quote) + "</mark>"
                   + esc(text[pos+len(quote):pos+len(quote)+700]))
    else:
        context = esc(text[:1800])
    warning = ("Exact quote found once in article." if source.get("quote_occurrences") == 1 else
               "Quote is absent verbatim or occurs more than once. Check full article; do not infer unique mapping.")
    return (f"<h3>{esc(record['date'])} · {esc(record['publisher'])}</h3>"
            f"<p>{esc(record['audit_id'])} · Article {esc(str(record['page_id']))}</p>"
            f"<p><b>Retrieval:</b> {esc(source['reason'])}</p><h4>Extracted passage</h4>"
            f"<blockquote style='white-space:pre-wrap'>{esc(quote or 'Unavailable')}</blockquote>"
            f"<p>{esc(warning)}</p><h4>Article context</h4>"
            f"<div style='white-space:pre-wrap'>{context}</div>"
            f"<details><summary>Read full article</summary><div style='white-space:pre-wrap'>{esc(text)}</div></details>"
            f"<details><summary>Source address (filled automatically)</summary><p>{esc(source['locator'])}</p>"
            f"<p>{esc(source.get('raw_locator', ''))}</p></details>")


def launch(project, bundle=None):
    """Display the fixed pilot. Run this notebook only inside the TDM workbench."""
    import ipywidgets as w
    from IPython.display import display
    bundle = Path(bundle or Path(__file__).resolve().parent)
    pack = load_pack(bundle / "pack.json")
    store = ReviewStore(bundle / "responses", pack)
    records = pack["records"]
    cache, active = {}, {"index": 0}
    reviewer = w.Text(description="Your name", placeholder="Actual reviewer", continuous_update=False)
    status = w.HTML()
    body = w.VBox()
    heading = w.HTML("<h2>ProQuest source review</h2><p>12 fixed pilot claims. Read the passage, answer in your own terms, "
                     "then lock your assessment to see machine labels. No economic outcomes are shown. "
                     "Drafts and locked responses stay in this VM. Do not download this notebook after running it.</p>")
    previous, following = w.Button(description="Previous"), w.Button(description="Next")
    progress = w.HTML()

    def show(index):
        active["index"] = index
        r = records[index]
        aid = r["audit_id"]
        previous.disabled, following.disabled = index == 0, index == len(records)-1
        locked_count = sum(bool(store.events(x["audit_id"], "first_pass")) for x in records)
        progress.value = f"<b>Claim {index+1} / {len(records)}</b> · {locked_count} first passes locked"
        if aid not in cache:
            cache[aid] = recover(project, r)
        source = cache[aid]
        locked = store.events(aid, "first_pass")
        drafts = store.events(aid, "draft")
        prior = (locked or drafts)[-1]["value"] if locked or drafts else {}
        if not reviewer.value:
            reviewer.value = prior.get("reviewer", "")
        started = prior.get("started_at", now())
        answers = prior.get("answers", {})
        fields = {}
        labels = {"mapping_status": "Is this the right passage?", "blinding": "Have you seen its machine labels?",
                  "is_forecast": "Does it make a future economic claim?", "quantity": "What exactly is predicted?",
                  "change_type": "Level, growth rate, or event?", "direction": "Direction of that quantity",
                  "scope": "Geographic / asset scope", "horizon_support": "How is the timing supported?",
                  "horizon_wording": "Timing words in the passage", "target_start": "Target start (leave unknown blank)",
                  "target_end": "Target end (leave unknown blank)", "condition": "Is it conditional?",
                  "condition_text": "Condition, if any", "attribution": "Who said it? Reported or endorsed?",
                  "original_forecast_date": "Earlier forecast date, if known",
                  "initial_note": "Brief evidence / uncertainty / mapping reason"}
        order = ("mapping_status", "blinding", "is_forecast", "quantity", "change_type", "direction", "scope",
                 "horizon_support", "horizon_wording", "target_start", "target_end", "condition", "condition_text",
                 "attribution", "original_forecast_date", "initial_note")
        controls = []
        for key in order:
            if key in CHOICES:
                widget = w.Dropdown(options=[("Choose…", "")] + [(v.replace('_', ' '), v) for v in CHOICES[key]],
                                    value=answers.get(key, ""), disabled=bool(locked), layout=w.Layout(width="98%"))
            else:
                widget = w.Textarea(value=answers.get(key, ""), rows=2 if key in {"initial_note", "attribution"} else 1,
                                    disabled=bool(locked), layout=w.Layout(width="98%"), continuous_update=False)
            fields[key] = widget
            controls.extend([w.HTML(f"<b>{html.escape(labels[key])}</b>"), widget])

        def snapshot():
            return {"reviewer": reviewer.value, "started_at": started,
                    "elapsed_seconds": max(0, (datetime.now(timezone.utc)-datetime.fromisoformat(started)).total_seconds()),
                    "answers": {k: v.value for k, v in fields.items()},
                    "provenance": {k: v for k, v in source.items() if k not in {"quote", "article"}}}

        def save_draft(change=None):
            if not locked:
                unavailable = fields["mapping_status"].value in {"ambiguous", "unavailable", "wrong_article"}
                for key, widget in fields.items():
                    if key not in {"mapping_status", "blinding", "initial_note"}:
                        widget.disabled = unavailable
                try:
                    store.record(aid, "draft", snapshot())
                    status.value = "Draft saved in VM."
                except ValueError as exc:
                    status.value = f"<b>{html.escape(str(exc))}</b>"

        for widget in fields.values():
            widget.observe(save_draft, names="value")
        save = w.Button(description="Save & lock first pass", button_style="success", disabled=bool(locked),
                        layout=w.Layout(width="230px"))
        reveal = w.Button(description="Reveal machine labels", disabled=not bool(locked) or answers.get("mapping_status") != "unique",
                          layout=w.Layout(width="230px"))
        compare_box = w.VBox()

        def commit(button):
            try:
                store.record(aid, "first_pass", snapshot())
                status.value = "First pass saved and locked. You can now reveal machine labels."
                show(index)
            except ValueError as exc:
                status.value = f"<b>{html.escape(str(exc))}</b>"

        def compare(button):
            try:
                machine = store.comparison(aid, bundle / "comparison.json")
            except ValueError as exc:
                status.value = html.escape(str(exc))
                return
            reveal.disabled = True
            saved = [e for e in store.events(aid) if e["kind"] in {"comparison", "comparison_draft"}]
            grades = saved[-1]["value"] if saved else {}
            widgets, rows = {}, [w.HTML("<h3>Compare with machine labels</h3><pre>" + html.escape(
                json.dumps({k: v for k, v in machine.items() if k != "audit_id"}, indent=2)) + "</pre>")]
            for key, options in COMPARISONS.items():
                widget = w.Dropdown(options=[("Choose…", "")] + [(v.replace('_', ' '), v) for v in options],
                                    value=grades.get(key, ""), layout=w.Layout(width="98%"))
                widgets[key] = widget
                rows.extend([w.HTML(f"<b>{key.replace('_', ' ').capitalize()}</b>"), widget])
            note = w.Textarea(placeholder="Comparison note / correction to locked first pass", value=grades.get("note", ""),
                              layout=w.Layout(width="98%"))
            finish = w.Button(description="Save comparison", button_style="success")

            def comparison_draft(change):
                try:
                    store.record(aid, "comparison_draft", dict({k: v.value for k, v in widgets.items()}, note=note.value))
                    status.value = "Comparison draft saved in VM."
                except ValueError as exc:
                    status.value = html.escape(str(exc))
            for widget in list(widgets.values()) + [note]:
                widget.observe(comparison_draft, names="value")

            def finish_comparison(button):
                try:
                    store.record(aid, "comparison", dict({k: v.value for k, v in widgets.items()}, note=note.value))
                    status.value = "Comparison saved in VM. Use Next when ready. Earlier saves remain in the audit trail."
                except ValueError as exc:
                    status.value = html.escape(str(exc))
            finish.on_click(finish_comparison)
            compare_box.children = tuple(rows + [note, finish])

        save.on_click(commit)
        reveal.on_click(compare)
        extras = []
        if locked:
            correction = w.Textarea(placeholder="Optional correction to the locked first pass", continuous_update=False)
            amend = w.Button(description="Append correction note")

            def append_correction(button):
                try:
                    if not correction.value.strip() or not reviewer.value.strip():
                        raise ValueError("Enter your name and correction note")
                    store.record(aid, "correction", {"reviewer": reviewer.value, "note": correction.value})
                    status.value = "Correction appended; original first pass preserved."
                    correction.value = ""
                except ValueError as exc:
                    status.value = html.escape(str(exc))
            amend.on_click(append_correction)
            extras = [correction, amend]
        left = w.HTML(source_html(r, source), layout=w.Layout(width="53%", padding="16px", max_height="800px", overflow="auto"))
        right = w.VBox(controls + [save, reveal, compare_box] + extras, layout=w.Layout(width="45%", padding="16px", max_height="800px", overflow="auto"))
        body.children = (w.HBox([left, right], layout=w.Layout(width="100%", align_items="flex-start")),)
        if store.events(aid, "reveal"):
            compare(None)

    previous.on_click(lambda b: show(active["index"]-1))
    following.on_click(lambda b: show(active["index"]+1))
    display(w.VBox([heading, reviewer, w.HBox([previous, following, progress]), status, body]))
    show(0)
    return store
