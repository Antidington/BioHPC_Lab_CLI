from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from bhlab.capabilities import detect
from bhlab.config import Config
from bhlab.deps import config_mk, load_profile, render_makefile


class BuildError(RuntimeError):
    pass


@dataclass
class BuildResult:
    platform: str
    makefile: Path
    config_mk: Path
    ran_make: bool
    stdout: str = ""


def prepare(config: Config, platform: str) -> tuple[Path, Path]:
    profile = load_profile(config.root, platform)
    caps = detect()
    config.build.mkdir(parents=True, exist_ok=True)
    config_mk_path = config.build / f"config.{platform}.mk"
    makefile_path = config.build / f"Makefile.{platform}"
    config_mk_path.write_text(config_mk(caps, profile), encoding="utf-8")
    makefile_path.write_text(render_makefile(profile, caps), encoding="utf-8")
    return makefile_path, config_mk_path


def build(
    config: Config,
    platform: str | None = None,
    emit_only: bool = False,
    jobs: int = 4,
    with_charm: bool = False,
) -> BuildResult:
    selected = platform or config.platform
    makefile_path, config_path = prepare(config, selected)
    if emit_only:
        return BuildResult(selected, makefile_path, config_path, ran_make=False)
    command = ["make", "-f", str(makefile_path), "-j", str(jobs)]
    result = subprocess.run(command, check=False, cwd=config.root, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise BuildError(f"build failed for {selected}\n{output}")
    if with_charm:
        charm = subprocess.run(
            ["make", "-f", str(makefile_path), "charm"], check=False, cwd=config.root,
            capture_output=True, text=True,
        )
        output += charm.stdout + charm.stderr
        if charm.returncode != 0:
            raise BuildError(f"charm build failed for {selected}\n{output}")
    return BuildResult(selected, makefile_path, config_path, ran_make=True, stdout=output)
