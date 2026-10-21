"""Package code and the unchanged twelve-record pilot into one uploadable notebook.

No articles, quotes, human answers, or economic outcomes are bundled.
"""
import base64
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(wheel_directory=None, output=None):
    inputs = {
        "proquest_tdm_review.py": ROOT / "src/proquest_tdm_review.py",
        "pack.json": ROOT / "data/scored/proquest/source_review_pilot_v1/pack.json",
        "comparison.json": ROOT / "data/scored/proquest/source_review_pilot_v1/comparison.json",
    }
    payload = {name: base64.b64encode(path.read_bytes()).decode() for name, path in inputs.items()}
    install = '''from pathlib import Path
import base64, hashlib, importlib, json, sys
PROJECT = Path('/home/ec2-user/SageMaker/election_arm')
if not PROJECT.is_dir():
    raise RuntimeError('Open this notebook inside the ProQuest TDM election_arm workbench.')
BUNDLE = PROJECT / 'source_review_pilot_tdm_v1'
BUNDLE.mkdir(exist_ok=True)
PAYLOAD = ''' + repr(payload) + '''
decoded = {name: base64.b64decode(data) for name, data in PAYLOAD.items()}
for name, data in decoded.items():
    destination = BUNDLE / name
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError('Existing installation differs: ' + name + '. Preserve responses and resolve version first.')
for name, data in decoded.items():
    destination = BUNDLE / name
    if not destination.exists():
        with destination.open('xb') as handle:
            handle.write(data)
sys.path.insert(0, str(BUNDLE))
import proquest_tdm_review
importlib.reload(proquest_tdm_review)
print('Ready. Responses remain in', BUNDLE / 'responses')
'''
    notebook = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "cells": [
            {"id": "instructions", "cell_type": "markdown", "metadata": {}, "source": [
                "# ProQuest human source review\n",
                "Run all cells to open the review. The original twelve pilot claims are preserved. "
                "Read each passage, answer the questions, then save and lock before revealing machine labels.\n\n",
                "Source text and answers stay inside this workbench. **Do not download this notebook after running it.** "
                "Reopening it resumes saved responses. This does not run extraction, verification, or paid model calls.\n"]},
            {"id": "install", "cell_type": "code", "metadata": {"jupyter": {"source_hidden": True}},
             "execution_count": None, "outputs": [], "source": install.splitlines(keepends=True)},
            {"id": "review", "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
             "source": ["review = proquest_tdm_review.launch(PROJECT, BUNDLE)\n"]},
        ],
    }
    if wheel_directory:
        wheels = {}
        for prefix in ("ipywidgets", "comm", "jupyterlab_widgets"):
            matches = list(Path(wheel_directory).glob(prefix + "-*-py3-none-any.whl"))
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one official pure-Python wheel for {prefix}")
            path = matches[0]
            data = path.read_bytes()
            wheels[path.name] = {"sha256": hashlib.sha256(data).hexdigest(),
                                 "base64": base64.b64encode(data).decode()}
        setup = "WHEELS = " + repr(wheels) + "\n" + (ROOT / "validation/proquest_review/offline_widgets.py").read_text()
        notebook["cells"].insert(2, {"id": "offline-widgets", "cell_type": "code",
            "metadata": {"jupyter": {"source_hidden": True}}, "execution_count": None,
            "outputs": [], "source": setup.splitlines(keepends=True)})
        notebook["metadata"]["kernelspec"] = {"display_name": "conda_python3", "language": "python", "name": "conda_python3"}
    out = Path(output) if output else ROOT / "validation/proquest_review/ProQuest_Source_Review.ipynb"
    out.write_text(json.dumps(notebook, indent=1) + "\n")
    print(f"Built {out} ({out.stat().st_size:,} bytes)")
    return notebook


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.wheel_directory, args.output)
