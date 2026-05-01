import os, sys, shutil, tempfile, itertools, importlib.util
from base64 import b85decode

ROOT = os.path.abspath('piptmp_root')
os.makedirs(ROOT, exist_ok=True)
_counter = itertools.count()

def good_mkdtemp(suffix=None, prefix=None, dir=None):
    base_dir = dir or ROOT
    prefix = prefix or "tmp"
    suffix = suffix or ""
    while True:
        name = f"{prefix}{next(_counter)}{suffix}"
        path = os.path.join(base_dir, name)
        try:
            os.makedirs(path, exist_ok=False)
            return path
        except FileExistsError:
            continue

tempfile.tempdir = ROOT
tempfile.mkdtemp = good_mkdtemp

spec = importlib.util.spec_from_file_location("get_pip", os.path.join(os.path.dirname(__file__), "get-pip.py"))
get_pip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(get_pip)
DATA = get_pip.DATA

pip_zip = os.path.join(ROOT, 'pip.zip')
with open(pip_zip, 'wb') as fp:
    fp.write(b85decode(DATA.replace(b"\n", b"")))

sys.path.insert(0, pip_zip)
from pip._internal.cli.main import main as pip_entry_point

args = ["install", "--upgrade", "pip"]
sys.exit(pip_entry_point(args))
