"""
Non-Python content must not enter the analysis.

The GUI used to warn, in red, that every non-Python structure had to be
excluded by hand "otherwise errors will occur". No error ever occurred:
binaries, JSON and even *directories* whose name ended in '.py' were
indexed as modules with no dependencies, and the report then advised
removing them as "isolated modules". Silent nonsense rather than a
failure - which is worse, because it looks like a result.
"""

from contextor.core.source import SourceError, parse_source, read_source
from contextor.core.symbol_engine.indexer import index_repository


def _repo(tmp_path):
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "a.py").write_text("def real():\n    return 1\n", encoding="utf-8")
    return root


def _skipped_paths(index):
    return {item.path.replace("\\", "/") for item in index.skipped}


def test_directory_named_like_a_module_is_not_a_module(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "weird_dir.py").mkdir()
    (root / "weird_dir.py" / "inside.txt").write_text("junk", encoding="utf-8")

    index = index_repository(str(root))

    assert "weird_dir" not in index.modules
    assert set(index.modules) == {"pkg.__init__", "pkg.a"}


def test_binary_file_is_skipped_and_reported(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "blob.py").write_bytes(b"\x00\x01\x02\xff\xfe binary")

    index = index_repository(str(root))

    assert "blob" not in index.modules
    assert "blob.py" in _skipped_paths(index)


def test_unparsable_file_is_skipped_and_reported(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "broken.py").write_text("this is not python {{{ <<< ]]]\n", encoding="utf-8")

    index = index_repository(str(root))

    assert "broken" not in index.modules

    reasons = {item.path.replace("\\", "/"): item.reason for item in index.skipped}
    assert "not valid Python" in reasons["broken.py"]


def test_unparsable_file_keeps_its_parser_line_number(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "broken.py").write_text(
        "def broken():\n    return [1, 2\n", encoding="utf-8"
    )

    index = index_repository(str(root))

    skipped = next(item for item in index.skipped if item.path == "broken.py")
    assert skipped.line_number == 2
    assert skipped.column_number == 12


def test_skip_reason_does_not_repeat_the_path(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "blob.py").write_bytes(b"\x00\x01\x02\xff\xfe")

    index = index_repository(str(root))

    for item in index.skipped:
        assert str(root) not in item.reason


# ==========================================================
# VALID PYTHON THAT IS NOT PLAIN UTF-8
# ==========================================================


def test_utf8_bom_file_is_analyzed(tmp_path, isolated_dirs):
    """
    CPython accepts a leading UTF-8 BOM, so Contextor must too.
    """

    root = _repo(tmp_path)
    (root / "bom.py").write_bytes(b"\xef\xbb\xbfimport os\n\n\ndef bom_ok():\n    return os.sep\n")

    index = index_repository(str(root))

    assert "bom" in index.modules
    assert not index.skipped
    assert [imp.module for imp in index.modules["bom"].imports] == ["os"]


def test_pep263_encoding_declaration_is_honoured(tmp_path, isolated_dirs):
    """
    CPython honours '# -*- coding: cp1250 -*-'; so must Contextor.
    """

    root = _repo(tmp_path)
    source = "# -*- coding: cp1250 -*-\n# żółw\nimport sys\n"
    (root / "legacy.py").write_bytes(source.encode("cp1250"))

    index = index_repository(str(root))

    assert "legacy" in index.modules
    assert not index.skipped
    assert [imp.module for imp in index.modules["legacy"].imports] == ["sys"]


def test_read_source_decodes_a_bom_file(tmp_path):
    target = tmp_path / "bom.py"
    target.write_bytes(b"\xef\xbb\xbfx = 1\n")

    assert read_source(target) == "x = 1\n"


def test_parse_source_rejects_binary_with_a_reason(tmp_path):
    target = tmp_path / "blob.py"
    target.write_bytes(b"\x00\x01\x02\xff\xfe")

    try:
        parse_source(target)
    except SourceError as exc:
        assert str(exc)
    else:
        raise AssertionError("binary content must not parse")


def test_missing_file_reports_a_reason(tmp_path):
    try:
        read_source(tmp_path / "nope.py")
    except SourceError as exc:
        assert "could not be read" in str(exc)
    else:
        raise AssertionError("a missing file must raise")
