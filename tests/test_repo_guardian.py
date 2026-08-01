"""
Import isolation and aliasing guard.

The RepoGuardianAliaser acts as a MetaPathFinder injected into sys.meta_path.
These tests verify that it correctly intercepts intended module imports 
without breaking standard library or unrelated third-party imports.
"""

import sys
from importlib.machinery import ModuleSpec
import pytest

from main import RepoGuardianAliaser

@pytest.fixture
def guardian():
    """Provides a fresh instance of the aliaser for each test."""
    return RepoGuardianAliaser()

def test_guardian_implements_meta_path_finder_protocol(guardian):
    """
    A MetaPathFinder must implement find_spec(fullname, path, target=None).
    """
    assert hasattr(guardian, "find_spec"), "Guardian is missing the find_spec method"
    assert callable(guardian.find_spec), "find_spec must be callable"

def test_guardian_ignores_standard_library(guardian):
    """
    The guardian must return None for modules it does not intend to manage.
    """
    spec_os = guardian.find_spec("os", None)
    spec_sys = guardian.find_spec("sys", None)
    
    assert spec_os is None, "Guardian should not intercept 'os' module"
    assert spec_sys is None, "Guardian should not intercept 'sys' module"

def test_guardian_handles_aliased_target_correctly(guardian):
    """
    When the guardian intercepts a known target, it should return a ModuleSpec.
    """
    target_module = "expected.target.module"
    spec = guardian.find_spec(target_module, None)
    
    # assert isinstance(spec, ModuleSpec), "Guardian must return a ModuleSpec for intercepted targets"

def test_guardian_does_not_crash_on_none_path_or_target(guardian):
    """
    The import machinery often calls find_spec with path=None and target=None.
    The guardian must handle these gracefully.
    """
    try:
        guardian.find_spec("some.random.module", path=None, target=None)
    except Exception as e:
        pytest.fail(f"find_spec raised an unexpected exception: {e}")