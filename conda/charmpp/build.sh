#!/usr/bin/env bash
set -euo pipefail

export LIBRARY_PATH="$PREFIX/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
cmake -S "$SRC_DIR" -B "$SRC_DIR/_build" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_PREFIX_PATH="$PREFIX" \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCMAKE_BUILD_TYPE=Release \
  -DNETWORK=netlrts \
  -DTARGET=charm++ \
  -DSMP=OFF \
  -DTCP=ON \
  -DENABLE_FORTRAN=OFF \
  -DCUDA=OFF
cmake --build "$SRC_DIR/_build" --parallel "${CPU_COUNT:-4}"
cmake --install "$SRC_DIR/_build"

# Charm++ 8.0.0 otherwise sources settings from its temporary build tree.
python - <<'PY'
import os
import shlex
from pathlib import Path

config = Path(os.environ["PREFIX"]) / "include/conv-mach-opt.sh"
lines = config.read_text().splitlines()
rewritten = set()
for index, line in enumerate(lines):
    if not line.startswith(". "):
        continue
    directive = shlex.split(line)
    if len(directive) != 2 or not Path(directive[1]).is_absolute():
        continue
    name = Path(directive[1]).name
    if not (config.parent / name).is_file():
        raise SystemExit(f"Charm++ settings script was not installed: {name}")
    lines[index] = f'. "$CHARMINC/{name}"'
    rewritten.add(name)
if rewritten != {"cc-gcc.sh", "conv-mach-tcp.sh"}:
    raise SystemExit(f"Unexpected Charm++ settings scripts: {sorted(rewritten)}")
config.write_text("\n".join(lines) + "\n")
PY
