from bhlab.bench import parse_matrix


def test_parse_matrix() -> None:
    matrix = parse_matrix("comm=local,mpi;device=cpu,gpu;layout=aos8,soa2")
    assert matrix["comm"] == ["local", "mpi"]
    assert matrix["device"] == ["cpu", "gpu"]
    assert matrix["layout"] == ["aos8", "soa2"]


def test_parse_matrix_defaults() -> None:
    matrix = parse_matrix("")
    assert matrix["comm"] == ["local"]
