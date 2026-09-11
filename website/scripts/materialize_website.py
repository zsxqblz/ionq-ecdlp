"""Create a standalone deployment copy without changing development symlinks."""
from pathlib import Path
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');args=p.parse_args()
src=Path(args.source).resolve();dst=Path(args.destination).resolve()
if dst.exists():raise SystemExit('Destination must be new; no files were overwritten.')
shutil.copytree(src,dst,symlinks=False,ignore=shutil.ignore_patterns('dist','node_modules','__pycache__'))
assert not any(p.is_symlink() for p in dst.rglob('*'))
print('Standalone source copy created:',dst)
