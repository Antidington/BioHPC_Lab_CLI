from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bhlab.config import Config

KNOWN_STEPS = {"scatter_reads", "shuffle_kmers", "gather_stats"}
STEP_RE = re.compile(r"^([a-z_]+)(?:\s+(.*))?$")
ARG_RE = re.compile(r"([a-z_]+)=([^\s]+)")


class CodegenError(ValueError):
    pass


@dataclass
class Pipeline:
    name: str
    input: str = ""
    steps: list[str] = field(default_factory=list)
    args: dict[str, dict[str, str]] = field(default_factory=dict)


def parse(path: Path) -> Pipeline:
    text = path.read_text(encoding="utf-8")
    name = ""
    input_path = ""
    steps: list[str] = []
    args: dict[str, dict[str, str]] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("pipeline"):
            match = re.match(r"pipeline\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", line)
            if not match:
                raise CodegenError(f"invalid pipeline declaration: {line}")
            name = match.group(1)
            continue
        if line == "}":
            continue
        if line.startswith("input"):
            match = re.match(r'input\s+"([^"]+)"', line)
            if not match:
                raise CodegenError(f"invalid input line: {line}")
            input_path = match.group(1)
            continue
        match = STEP_RE.match(line)
        if not match:
            raise CodegenError(f"unknown pipeline line: {line}")
        keyword, remainder = match.group(1), match.group(2) or ""
        if keyword not in KNOWN_STEPS:
            raise CodegenError(f"unknown keyword '{keyword}'; known: {', '.join(sorted(KNOWN_STEPS))}")
        if keyword not in steps:
            steps.append(keyword)
        args[keyword] = {key: value for key, value in ARG_RE.findall(remainder)}
    if not name:
        raise CodegenError("pipeline name is missing")
    if len(steps) < 2:
        raise CodegenError("a pipeline needs at least two domain communication keywords")
    return Pipeline(name=name, input=input_path, steps=steps, args=args)


def _render(config: Config, pipeline: Pipeline, comm: str, header: str) -> str:
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "codegen_templates"),
                      autoescape=False, keep_trailing_newline=True)
    template_name = {
        "local": "driver_local.cpp.j2",
        "mpi": "driver_mpi.cpp.j2",
        "charm": "driver_charm.cpp.j2",
    }.get(comm)
    if template_name is None:
        raise CodegenError("comm must be local, mpi, or charm")
    template = env.get_template(template_name)
    steps = ", ".join(f'"{step}"' for step in pipeline.steps)
    return template.render(
        name=pipeline.name, steps=steps, steps_csv=",".join(pipeline.steps), header=header,
    )


def generate(config: Config, pipeline_path: Path, comm: str, out: Path | None = None) -> list[Path]:
    pipeline = parse(pipeline_path)
    if out is None:
        out = config.build / "gen" / f"{pipeline.name}_{comm}.cpp"
    out = Path(out)
    if out.suffix == "":
        out = out.with_suffix(".cpp")
    source = _render(config, pipeline, comm, out.stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(source, encoding="utf-8")
    written = [out]
    if comm == "charm":
        ci = out.with_suffix(".ci")
        ci.write_text(_charm_ci(out.stem), encoding="utf-8")
        written.append(ci)
    return written


def _charm_ci(module: str) -> str:
    return f"""mainmodule {module} {{
  readonly int g_k;
  readonly int g_window;
  readonly int g_layout;
  readonly int g_device;
  readonly int g_threads;
  readonly int g_max_reads;
  readonly char g_input[4096];
  readonly char g_output[4096];
  readonly char g_events[4096];
  readonly char g_job_id[256];
  readonly char g_steps[512];

  mainchare main {{
    entry main(CkArgMsg*);
  }};

  array [1D] KmerChare {{
    entry KmerChare();
    entry void run();
    entry void merge(CkReductionMsg*);
  }};
}};
"""
