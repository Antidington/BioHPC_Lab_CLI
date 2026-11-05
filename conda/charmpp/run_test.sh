#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

cd examples/charm++/hello/1darray
if ! "$PREFIX/bin/charmc" hello.ci > compile.log 2>&1; then
  cat compile.log
  exit 1
fi
if ! "$PREFIX/bin/charmc" -c++-option -std=c++17 hello.C -o hello >> compile.log 2>&1; then
  cat compile.log
  exit 1
fi
cat compile.log
if grep -F 'No such file or directory' compile.log; then
  exit 1
fi
"$PREFIX/bin/charmrun" ++local +p2 ./hello 4 > hello.log 2>&1
cat hello.log
grep -F 'Running Hello on 2 processors for 4 elements' hello.log
grep -F 'All done' hello.log
