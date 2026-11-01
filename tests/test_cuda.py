import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from bhlab.logs.schema import LogEvent

pytestmark = pytest.mark.skipif(
    os.environ.get("BHLAB_TEST_CUDA") != "1",
    reason="set BHLAB_TEST_CUDA=1 to run CUDA hardware tests",
)


@pytest.fixture(scope="module")
def cuda_checkout() -> Path:
    root = Path(__file__).resolve().parents[1]
    for tool in ("nvcc", "nvidia-smi"):
        assert shutil.which(tool), f"CUDA tests require {tool} on PATH"
    binary = root / "build/bin/bhlab-kmer"
    assert binary.is_file() and os.access(binary, os.X_OK), (
        "build the gpu-cuda profile before running CUDA tests"
    )
    devices = subprocess.run(
        ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=30, check=False,
    )
    assert devices.returncode == 0 and "GPU " in devices.stdout, (
        devices.stdout + devices.stderr
    )
    return root


@pytest.fixture
def reads(tmp_path: Path) -> tuple[Path, list[str]]:
    sequence = "ACGTTGCAAGTCCTAGGATCCGATGTACCTGAGCTTAGGCTACGTATCGGATACCTGTAGCTACGATGC"
    sequences = [sequence[:length] for length in (1, 14, 15, 30, 31, 32, 33, 65)]
    sequences += [sequence, sequence, sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]]
    path = tmp_path / "reads.fa"
    path.write_text(
        "".join(f">read{i}\n{read}\n" for i, read in enumerate(sequences)),
        encoding="utf-8",
    )
    return path, sequences


def reference_tsv(reads: list[str], k: int) -> bytes:
    counts: Counter[str] = Counter()
    complement = str.maketrans("ACGT", "TGCA")
    for read in reads:
        for pos in range(len(read) - k + 1):
            forward = read[pos:pos + k]
            reverse = forward.translate(complement)[::-1]
            counts[min(forward, reverse)] += 1
    return ("kmer\tcount\n" + "".join(
        f"{kmer}\t{counts[kmer]}\n" for kmer in sorted(counts)
    )).encode("utf-8")


def run_cli(root: Path, input_path: Path, output: Path, device: str,
            layout: str, k: int, *, masked: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if masked:
        env["CUDA_VISIBLE_DEVICES"] = ""
    return subprocess.run(
        [
            sys.executable, "-m", "bhlab", "--root", str(root), "run",
            "--input", str(input_path), "--output", str(output),
            "--comm", "local", "--device", device, "--layout", layout, "--k", str(k),
        ],
        cwd=root, env=env, capture_output=True, text=True, timeout=90, check=False,
    )


def read_events(output: Path) -> list[LogEvent]:
    events = [
        LogEvent.from_json(line)
        for line in output.with_name("events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events
    assert all(event.source == "app" for event in events)
    return events


@pytest.mark.parametrize("k", [1, 15, 31])
@pytest.mark.parametrize("layout", ["aos8", "soa2"])
def test_cuda_counts_match_reference(cuda_checkout: Path, reads: tuple[Path, list[str]],
                                     tmp_path: Path, k: int, layout: str) -> None:
    input_path, sequences = reads
    expected = reference_tsv(sequences, k)
    outputs = {}
    for device in ("cpu", "gpu"):
        output = tmp_path / device / "counts.tsv"
        result = run_cli(cuda_checkout, input_path, output, device, layout, k)
        assert result.returncode == 0, result.stdout + result.stderr
        outputs[device] = output.read_bytes()
        assert outputs[device] == expected
        record = json.loads(output.with_name("run.json").read_text(encoding="utf-8"))
        assert record["returncode"] == 0
        assert record["checksum"] == hashlib.sha256(expected).hexdigest()
        assert record["plan"]["device"] == device
        assert record["plan"]["layout"] == layout
        events = read_events(output)
        start = next(event for event in events if event.event == "run_start")
        assert start.params["device"] == device
        assert start.params["layout"] == layout
        assert start.params["k"] == str(k)
        assert not any(event.level == "error" for event in events)
        end = next(event for event in events if event.event == "run_end")
        assert int(end.params["exit_code"]) == 0
    assert outputs["cpu"] == outputs["gpu"]


def test_cuda_masked_device_fails(cuda_checkout: Path, reads: tuple[Path, list[str]],
                                  tmp_path: Path) -> None:
    control = tmp_path / "visible" / "counts.tsv"
    visible = run_cli(cuda_checkout, reads[0], control, "gpu", "soa2", 15)
    assert visible.returncode == 0, visible.stdout + visible.stderr
    assert control.read_bytes() == reference_tsv(reads[1], 15)
    output = tmp_path / "masked" / "counts.tsv"
    result = run_cli(cuda_checkout, reads[0], output, "gpu", "soa2", 15, masked=True)
    assert result.returncode != 0, "masked GPU incorrectly reported CLI success"
    record = json.loads(output.with_name("run.json").read_text(encoding="utf-8"))
    assert record["returncode"] != 0
    assert record["checksum"] == ""
    assert not output.exists()
    events = read_events(output)
    start = next(event for event in events if event.event == "run_start")
    assert start.params["device"] == "gpu"
    assert start.params["layout"] == "soa2"
    errors = [event for event in events if event.event == "error"]
    assert errors
    assert all(event.level == "error" and int(event.params["exit_code"]) != 0 for event in errors)
    assert any("cuda" in event.message.lower() for event in errors)
    assert not any(event.event in ("phase_end", "run_end") for event in events)
