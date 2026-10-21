"""Embedded by the notebook builder; invoked only inside TDM with WHEELS and BUNDLE."""
import base64
import hashlib
import io
from pathlib import Path
import shutil
import sys
import zipfile

VENDOR = BUNDLE / 'widget_vendor'
VENDOR.mkdir(exist_ok=True)
for name, item in WHEELS.items():
    data = base64.b64decode(item['base64'])
    assert hashlib.sha256(data).hexdigest() == item['sha256'], name
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = (VENDOR / member.filename).resolve()
            if VENDOR.resolve() not in target.parents:
                raise ValueError('Unsafe wheel path')
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(member)
            if target.exists() and target.read_bytes() != content:
                raise ValueError('Different existing widget file: ' + str(target))
            target.write_bytes(content)
sys.path.insert(0, str(VENDOR))
import ipywidgets
print('Widget backend ready:', ipywidgets.__version__)
# Install only the frontend asset folder if the user has no existing manager.
asset = next(VENDOR.glob('jupyterlab_widgets-*.data/data/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager'))
frontend = Path.home() / '.local/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager'
if not frontend.exists():
    frontend.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(asset, frontend)
    print('Widget frontend installed. Refresh this Jupyter browser tab if widgets do not render.')
print('Human responses remain inside TDM.')
