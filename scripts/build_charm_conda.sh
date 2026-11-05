#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
case "$(uname -s):$(uname -m)" in
  Linux:x86_64) ;;
  *) printf '%s\n' 'Build this Charm++ package on a Linux x86_64 target host.' >&2; exit 1 ;;
esac

manager=${MAMBA_EXE:-}
if [[ -z "$manager" ]]; then
  manager=$(command -v mamba || command -v micromamba || true)
fi
if [[ -z "$manager" ]]; then
  printf '%s\n' 'mamba or micromamba is required to build the local Charm++ package.' >&2
  exit 1
fi

builder="$repo_root/build/conda-build-env"
channel="$repo_root/build/conda-channel"
export CONDA_PKGS_DIRS="${CONDA_PKGS_DIRS:-$repo_root/build/_conda-pkgs}"
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$repo_root/build/_mamba-root}"
export CPU_COUNT="${CPU_COUNT:-4}"
if [[ ! -x "$builder/bin/conda-build" ]]; then
  "$manager" create --yes --override-channels -c conda-forge \
    --prefix "$builder" conda-build
fi

mkdir -p "$channel"
"$builder/bin/conda-build" "$repo_root/conda/charmpp" \
  --no-anaconda-upload --override-channels -c conda-forge \
  --croot "$repo_root/build/conda-build" --output-folder "$channel"
printf 'Charm++ package is available in %s\n' "$channel"
