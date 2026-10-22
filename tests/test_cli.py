from pathlib import Path

from typer.testing import CliRunner

from bhlab.cli import app


def test_version(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_help_lists_core_commands(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "--help"])
    assert result.exit_code == 0
    for command in ("build", "run", "bench", "log", "watch", "demo"):
        assert command in result.stdout
