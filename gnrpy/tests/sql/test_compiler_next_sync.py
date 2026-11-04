"""Surveillance over the two compiler modules while they are meant to be twins.

``compiler_next.py`` starts as a copy of ``compiler.py``: the only differences
allowed are the module docstring, the class name ``SqlQueryCompiler`` ->
``SqlQueryCompilerNext`` and blank lines.  Every fix backported into
``compiler.py`` has to reach the copy, and this test is what says so.

When the copy legitimately starts to diverge, this test is relaxed by a
deliberate commit -- not by deleting it in passing.
"""

import ast
import difflib

import pytest

from gnr.sql.gnrsqldata import compiler
from gnr.sql.gnrsqldata import compiler_next

LEGACY_CLASS = 'SqlQueryCompiler'
NEXT_CLASS = 'SqlQueryCompilerNext'


def _without_module_docstring(source):
    """Return *source* as a list of lines, module docstring removed."""
    lines = source.splitlines()
    body = ast.parse(source).body
    if not body:
        return lines
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
            and isinstance(first.value.value, str):
        del lines[first.lineno - 1:first.end_lineno]
    return lines


def _normalized(module, class_name):
    """The module source, without its docstring, blank lines or its own class name."""
    with open(module.__file__, encoding='utf-8') as source_file:
        source = source_file.read()
    lines = _without_module_docstring(source)
    if class_name != LEGACY_CLASS:
        lines = [line.replace(class_name, LEGACY_CLASS) for line in lines]
    return [line for line in lines if line.strip()]


def test_next_compiler_is_a_copy_of_the_legacy_one():
    legacy_lines = _normalized(compiler, LEGACY_CLASS)
    next_lines = _normalized(compiler_next, NEXT_CLASS)
    if legacy_lines != next_lines:
        diff = '\n'.join(difflib.unified_diff(
            legacy_lines, next_lines,
            fromfile='compiler.py', tofile='compiler_next.py', lineterm=''))
        pytest.fail(
            'compiler_next.py is no longer a copy of compiler.py.\n'
            'Backport the change, or relax this test in a commit of its own.\n'
            '%s' % diff)


def test_the_two_classes_are_distinct():
    legacy_class = getattr(compiler, LEGACY_CLASS)
    next_class = getattr(compiler_next, NEXT_CLASS)
    assert next_class is not legacy_class
    assert not issubclass(next_class, legacy_class)
    assert sorted(vars(next_class)) == sorted(vars(legacy_class))
