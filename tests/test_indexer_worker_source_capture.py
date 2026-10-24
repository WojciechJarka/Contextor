"""P1D1A: source bytes returned by an opted-in indexer worker."""

from __future__ import annotations

import hashlib

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    managed_reusable_process_pool,
    terminate_active_process_pools,
)
from contextor.core.paths import repo_cache_dir
from contextor.core.symbol_engine import indexer


def _source(tmp_path, raw=b"import os\nvalue = os.name\n"):
    root = tmp_path / "repo"
    root.mkdir()
    path = root / "sample.py"
    path.write_bytes(raw)
    return root, path


def _worker(root, path, maximum=None):
    return indexer._process_single_file(
        str(path),
        str(root),
        source_capture_max_bytes=maximum,
    )


def _assert_capture(result, raw):
    assert result["error"] is None
    assert result["source_capture_status"] == "CAPTURED"
    assert result["source_capture_bytes"] == raw
    assert type(result["source_capture_bytes"]) is bytes
    assert result["source_capture_origin"] == (
        "INDEXER_WORKER_READ"
    )
    assert result["source_fingerprint"] == (
        hashlib.sha256(raw).hexdigest()
    )
    assert hashlib.sha256(
        result["source_capture_bytes"]
    ).hexdigest() == result["source_fingerprint"]


def test_p1d1a_t01_default_result_has_no_capture_payload(
    tmp_path, isolated_dirs,
):
    root, path = _source(tmp_path)
    cold = _worker(root, path)
    warm = _worker(root, path)

    for result in (cold, warm):
        assert result["error"] is None
        assert not any(
            key.startswith("source_capture_")
            for key in result
        )


def test_p1d1a_t02_cold_capture_uses_worker_bytes(
    tmp_path, isolated_dirs,
):
    raw = b"import os\r\nvalue = os.name\r\n"
    root, path = _source(tmp_path, raw)
    result = _worker(root, path, 1024)

    _assert_capture(result, raw)
    assert result["source_parse_called"] is True
    assert result["source_capture_ast_mode"] == (
        "PARSED_FROM_WORKER_READ"
    )


def test_p1d1a_t03_warm_capture_labels_cache_equivalence(
    tmp_path, isolated_dirs,
):
    raw = b"import os\nvalue = os.name\n"
    root, path = _source(tmp_path, raw)
    first = _worker(root, path)
    assert first["error"] is None

    warm = _worker(root, path, 1024)

    _assert_capture(warm, raw)
    assert warm["source_parse_called"] is False
    assert warm["cache_hit"] is True
    assert warm["source_capture_ast_mode"] == (
        "CACHE_SHA256_EQUIVALENT"
    )


def test_p1d1a_t04_source_change_rebinds_capture(
    tmp_path, isolated_dirs,
):
    old = b"import os\nvalue = 1\n"
    new = b"import os\nvalue = 2\n"
    root, path = _source(tmp_path, old)

    before = _worker(root, path, 1024)
    path.write_bytes(new)
    after = _worker(root, path, 1024)

    _assert_capture(before, old)
    _assert_capture(after, new)
    assert before["source_fingerprint"] != (
        after["source_fingerprint"]
    )


def test_p1d1a_t05_over_budget_never_returns_raw(
    tmp_path, isolated_dirs,
):
    raw = b"import os\nvalue = os.name\n"
    root, path = _source(tmp_path, raw)
    result = _worker(root, path, len(raw) - 1)

    assert result["error"] is None
    assert result["source_capture_status"] == "BYTE_LIMIT"
    assert "source_capture_bytes" not in result
    assert "source_capture_ast_mode" not in result
    assert result["source_fingerprint"] == (
        hashlib.sha256(raw).hexdigest()
    )


def test_p1d1a_t06_empty_file_is_valid_capture(
    tmp_path, isolated_dirs,
):
    root, path = _source(tmp_path, b"")
    result = _worker(root, path, 1)

    _assert_capture(result, b"")
    assert result["imports"] == []


def test_p1d1a_t07_parse_error_returns_no_bytes(
    tmp_path, isolated_dirs,
):
    root, path = _source(
        tmp_path,
        b"def broken(:\n",
    )
    result = _worker(root, path, 1024)

    assert result["error"]
    assert result["source_capture_status"] == (
        "SOURCE_PARSE_FAILED"
    )
    assert "source_capture_bytes" not in result


def test_p1d1a_t08_read_failure_returns_no_bytes(
    tmp_path, isolated_dirs,
):
    root, path = _source(tmp_path)
    path.unlink()

    result = _worker(root, path, 1024)

    assert result["error"]
    assert result["source_capture_status"] == (
        "SOURCE_READ_FAILED"
    )
    assert "source_capture_bytes" not in result


def test_p1d1a_t09_optional_fact_failure_does_not_forge_source(
    tmp_path, isolated_dirs, monkeypatch,
):
    raw = b"import os\nvalue = os.name\n"
    root, path = _source(tmp_path, raw)

    def fail_symbol_extraction(*args, **kwargs):
        raise RuntimeError("injected symbol failure")

    monkeypatch.setattr(
        indexer,
        "extract_file_symbols",
        fail_symbol_extraction,
    )

    result = _worker(root, path, 1024)

    _assert_capture(result, raw)
    assert result["symbol_facts"]["status"] == "failure"


def test_p1d1a_t10_real_process_pool_transports_opted_bytes(
    tmp_path, isolated_dirs,
):
    raw = b"import os\nvalue = os.name\n"
    root, path = _source(tmp_path, raw)

    try:
        with managed_reusable_process_pool(
            "indexer"
        ) as (executor, _, _):
            future = executor.submit(
                indexer._process_single_file,
                str(path),
                str(root),
                None,
                None,
                str(repo_cache_dir(root)),
                1024,
            )
            result = future.result(timeout=90)

        _assert_capture(result, raw)
        assert result["source_capture_ast_mode"] in {
            "PARSED_FROM_WORKER_READ",
            "CACHE_SHA256_EQUIVALENT",
        }
    finally:
        terminate_active_process_pools(timeout=1.0)


def test_p1d1a_t11_invalid_capture_limits_rejected(
    tmp_path, isolated_dirs,
):
    root, path = _source(tmp_path)

    for maximum in (
        0,
        -1,
        True,
        False,
        1.0,
        64 * 1024 * 1024 + 1,
    ):
        with pytest.raises(ValueError):
            _worker(root, path, maximum)


def test_p1d1a_t12_capture_performs_no_second_read(
    tmp_path, isolated_dirs, monkeypatch,
):
    raw = b"import os\nvalue = os.name\n"
    root, path = _source(tmp_path, raw)

    calls = []
    original = indexer.read_source_snapshot

    def traced(path_arg):
        calls.append(path_arg)
        return original(path_arg)

    monkeypatch.setattr(
        indexer,
        "read_source_snapshot",
        traced,
    )

    result = _worker(root, path, 1024)

    _assert_capture(result, raw)
    assert len(calls) == 1


def test_p1d1a_t13_index_error_cannot_return_capture(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, path = _source(tmp_path)

    monkeypatch.setattr(
        indexer,
        "read_imports",
        lambda *args, **kwargs: (
            None, "injected import failure"
        ),
    )

    result = _worker(root, path, 1024)

    assert result["error"] == "injected import failure"
    assert result["source_capture_status"] == (
        "INDEX_FAILED"
    )
    assert "source_capture_bytes" not in result
