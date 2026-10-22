from pathlib import Path

import pytest

from bhlab.codegen import CodegenError, generate, parse
from bhlab.config import Config


def write_pipeline(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "pipeline.bhl"
    path.write_text(body, encoding="utf-8")
    return path


def test_parse_keywords(tmp_path: Path) -> None:
    path = write_pipeline(tmp_path, """
    pipeline test {
      input "reads.fq"
      scatter_reads chunk=1000
      shuffle_kmers key=canonical
      gather_stats
    }
    """)
    pipeline = parse(path)
    assert pipeline.name == "test"
    assert pipeline.steps == ["scatter_reads", "shuffle_kmers", "gather_stats"]
    assert pipeline.args["scatter_reads"]["chunk"] == "1000"


def test_unknown_keyword_fails(tmp_path: Path) -> None:
    path = write_pipeline(tmp_path, """
    pipeline bad {
      input "reads.fq"
      teleport_reads
      shuffle_kmers
    }
    """)
    with pytest.raises(CodegenError):
        parse(path)


def test_needs_two_keywords(tmp_path: Path) -> None:
    path = write_pipeline(tmp_path, """
    pipeline short {
      input "reads.fq"
      scatter_reads
    }
    """)
    with pytest.raises(CodegenError):
        parse(path)


def test_local_and_mpi_rendering(tmp_path: Path) -> None:
    path = write_pipeline(tmp_path, """
    pipeline demo {
      input "reads.fq"
      scatter_reads
      shuffle_kmers
    }
    """)
    config = Config(root=tmp_path)
    local = generate(config, path, "local", tmp_path / "demo_local.cpp")
    mpi = generate(config, path, "mpi", tmp_path / "demo_mpi.cpp")
    assert "run_local" in local[0].read_text()
    assert "run_mpi" in mpi[0].read_text()
    assert '"scatter_reads", "shuffle_kmers"' in local[0].read_text()


def test_charm_writes_ci(tmp_path: Path) -> None:
    path = write_pipeline(tmp_path, """
    pipeline demo {
      input "reads.fq"
      scatter_reads
      shuffle_kmers
    }
    """)
    config = Config(root=tmp_path)
    paths = generate(config, path, "charm", tmp_path / "demo_charm.cpp")
    assert len(paths) == 2
    assert paths[1].suffix == ".ci"
    text = paths[0].read_text()
    assert "CkReduction" in text
    assert "readonly" in text or "g_steps" in text
    assert "mainmodule" in paths[1].read_text()
