from contextor.core.reporting_layer.reporting_llm import generate_llm_markdown


def test_markdown_uses_real_module_name_and_flattens_api_surface(tmp_path):
    output = tmp_path / "single_pkg.alpha_llm_context.md"
    report = {
        "module_id": "17/1",
        "module_name": "pkg.alpha",
        "llm_summary": {
            "purpose": "Alpha module.",
            "api_surface": {
                "functions": {"build": {"kind": "function", "line_start": 7, "signature": "build(value)"}},
                "methods": {"Engine.run": {"kind": "method", "line_start": 20, "signature": "run(self)"}},
                "classes": {"Engine": {"kind": "class", "line_start": 12}},
            },
            "module_dependency_radius": 4,
            "direct_dependents": ["a"],
            "transitive_dependents": ["b", "c", "d"],
        },
    }

    generate_llm_markdown(report, str(output))
    markdown = output.read_text(encoding="utf-8")

    assert "# Module Context Bundle: `pkg.alpha`" in markdown
    assert "| `build` | function | 7 | `build(value)`" in markdown
    assert "| `Engine.run` | method | 20 | `run(self)`" in markdown
    assert "| `functions` |" not in markdown
    assert "Module Dependency Radius:** 4" in markdown
    assert "`single_pkg.alpha.json`" in markdown
    assert "unknown" not in markdown


def test_markdown_reports_no_api_for_empty_grouped_surface(tmp_path):
    output = tmp_path / "single_pkg.empty_llm_context.md"
    report = {
        "module_name": "pkg.empty",
        "llm_summary": {"api_surface": {"functions": {}, "methods": {}, "classes": {}}},
    }

    generate_llm_markdown(report, str(output))

    assert "No public API detected." in output.read_text(encoding="utf-8")
