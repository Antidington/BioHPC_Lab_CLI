from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field


@dataclass
class Library:
    name: str
    found: bool
    version: str = ""
    cflags: str = ""
    libs: str = ""
    detail: str = ""


@dataclass
class Capabilities:
    mpi: bool = False
    charm: bool = False
    charm_launcher: str = ""
    cuda: bool = False
    openmp: bool = False
    slurm: bool = False
    compilers: dict[str, str] = field(default_factory=dict)
    libraries: dict[str, Library] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["libraries"] = {key: asdict(value) for key, value in self.libraries.items()}
        return data

    def available_comm(self) -> list[str]:
        out = ["local"]
        if self.mpi:
            out.insert(0, "mpi")
        if self.charm:
            out.insert(0, "charm")
        return out

    def available_device(self) -> list[str]:
        return ["gpu", "cpu"] if self.cuda else ["cpu"]


LIBRARY_SPECS = [
    ("zlib", "zlib.h", "z"),
    ("libdeflate", "libdeflate.h", "deflate"),
    ("bzip2", "bzlib.h", "bz2"),
    ("lzma", "lzma.h", "lzma"),
    ("htslib", "htslib/sam.h", "hts"),
]


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=30, **kwargs)


def _pkg_config(name: str) -> tuple[str, str, str] | None:
    if shutil.which("pkg-config") is None:
        return None
    exists = _run(["pkg-config", "--exists", name])
    if exists.returncode != 0:
        return None
    version = _run(["pkg-config", "--modversion", name]).stdout.strip()
    cflags = _run(["pkg-config", "--cflags", name]).stdout.strip()
    libs = _run(["pkg-config", "--libs", name]).stdout.strip()
    return version, cflags, libs


def _compile_probe(header: str, library: str) -> tuple[bool, str]:
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        return False, "no C++ compiler"
    source = f"#include <{header}>\nint main() {{ return 0; }}\n"
    prefixes = [
        [],
        ["-I/opt/homebrew/include", "-L/opt/homebrew/lib"],
        ["-I/opt/homebrew/opt/xz/include", "-L/opt/homebrew/opt/xz/lib"],
        ["-I/usr/local/include", "-L/usr/local/lib"],
    ]
    conda = os.environ.get("CONDA_PREFIX")
    if conda:
        prefixes.append([f"-I{conda}/include", f"-L{conda}/lib"])
    detail = "not found"
    for prefix in prefixes:
        result = _run(
            [compiler, *prefix, "-x", "c++", "-", "-o", "/dev/null", f"-l{library}"],
            input=source,
        )
        if result.returncode == 0:
            flags = " ".join(prefix)
            return True, flags
        detail = result.stderr.strip()
    return False, detail


def probe_library(name: str, header: str, library: str) -> Library:
    pkg = _pkg_config(name if name != "bzip2" else "bzip2")
    if pkg is not None:
        version, cflags, libs = pkg
        return Library(name=name, found=True, version=version, cflags=cflags, libs=libs,
                       detail="pkg-config")
    found, flags = _compile_probe(header, library)
    if found:
        return Library(name=name, found=True, version="detected", cflags=flags,
                       libs=f"-l{library}", detail="compile probe")
    return Library(name=name, found=False, detail=flags or "not found")


def _has_openmp() -> bool:
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        return False
    source = "#include <omp.h>\nint main() { return omp_get_max_threads() > 0 ? 0 : 1; }\n"
    result = _run([compiler, "-fopenmp", "-x", "c++", "-", "-o", "/dev/null"], input=source)
    return result.returncode == 0


def detect() -> Capabilities:
    caps = Capabilities()
    caps.mpi = shutil.which("mpicxx") is not None and shutil.which("mpirun") is not None
    caps.charm = shutil.which("charmc") is not None
    caps.charm_launcher = (
        "charmrun" if shutil.which("charmrun")
        else "prterun" if shutil.which("prterun")
        else ""
    )
    caps.cuda = shutil.which("nvcc") is not None and shutil.which("nvidia-smi") is not None
    caps.slurm = shutil.which("sbatch") is not None and shutil.which("sacct") is not None
    caps.openmp = _has_openmp()
    caps.compilers = {
        "cxx": shutil.which("c++") or "",
        "gxx": shutil.which("g++") or "",
        "clangxx": shutil.which("clang++") or "",
        "mpicxx": shutil.which("mpicxx") or "",
        "charmc": shutil.which("charmc") or "",
        "nvcc": shutil.which("nvcc") or "",
    }
    caps.libraries = {
        name: probe_library(name, header, lib)
        for name, header, lib in LIBRARY_SPECS
    }
    return caps
