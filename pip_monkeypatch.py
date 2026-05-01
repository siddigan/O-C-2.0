import os, sys, tempfile, itertools

ROOT = os.path.abspath('piptmp_root')
os.makedirs(ROOT, exist_ok=True)
_counter = itertools.count()

def good_mkdtemp(suffix=None, prefix=None, dir=None):
    base_dir = dir or ROOT
    prefix = prefix or "tmp"
    suffix = suffix or ""
    while True:
        path = os.path.join(base_dir, f"{prefix}{next(_counter)}{suffix}")
        try:
            os.makedirs(path, exist_ok=False)
            return path
        except FileExistsError:
            continue

tempfile.tempdir = ROOT
tempfile.mkdtemp = good_mkdtemp

from pip._internal.cli.main import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
