"""Page discovery and the two ratchet files, shared by the suites that assert on them.

`test_pages_documented.py` needs nothing but this module and the source tree;
`test_pages_smoke.py` adds a running site to render every page it finds here.
Keeping the two apart is what lets the documentation ratchet run in CI, where no
instance is built: a check that silently skips is a check that protects nothing.
"""
import ast
import glob
import os
import re

PACKAGES = ('test', 'test15')

# titles that render as a page heading but say nothing about the page
PLACEHOLDER_TITLES = ('test page description', 'test', '-', 'index.py', 'test page')

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGES_DIR = os.path.abspath(os.path.join(TESTS_DIR, *[os.pardir] * 2))
GENROPY_ROOT = os.path.abspath(os.path.join(PACKAGES_DIR, *[os.pardir] * 3))
COMMON_RESOURCES_DIR = os.path.join(GENROPY_ROOT, 'resources', 'common')
SMOKE_RATCHET = os.path.join(TESTS_DIR, 'smoke_known_failures.txt')
DOCSTRING_RATCHET = os.path.join(TESTS_DIR, 'docstring_debt.txt')

SKIP_FOLDERS = ('_resources', '__pycache__')

# a `package.table` reference as the pages spell it, e.g. glbl.provincia
TABLE_REFERENCE = re.compile(r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$')

# kwargs through which a page names the table it works on
TABLE_KEYWORDS = ('table', 'dbtable', 'dbTable')

# class attributes through which a page mixes in a component resource. Only
# py_requires matters here: an entry the loader cannot resolve is a hard raise
# (`GnrMixinNotFound`, gnrwsgisite_proxy/gnrresourceloader.py:mixinResource),
# while an unresolved css/js entry only leaves the page unstyled.
REQUIRES_ATTRIBUTES = ('py_requires',)

# every package that can provide a resource, whatever project it lives in:
# `site_resources` walks the mounted packages regardless of their project
PACKAGE_RESOURCES_GLOB = os.path.join(GENROPY_ROOT, 'projects', '*', 'packages', '*', 'resources')


def discover_pages():
    """Package-relative paths of every test page of PACKAGES, sorted"""
    pages = []
    for package in PACKAGES:
        webpages_dir = os.path.join(PACKAGES_DIR, package, 'webpages')
        for folder, dirnames, filenames in os.walk(webpages_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_FOLDERS]
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                full_path = os.path.join(folder, filename)
                pages.append(os.path.relpath(full_path, PACKAGES_DIR))
    return sorted(pages)


def page_url(page_path):
    """URL serving the page at the given package-relative path"""
    package, _, page = page_path.partition(os.sep + 'webpages' + os.sep)
    return '/%s/%s' % (package, page[:-len('.py')].replace(os.sep, '/'))


def docstring_defects(page_path):
    """Reasons why the page is undocumented in the test UI, if any"""
    with open(os.path.join(PACKAGES_DIR, page_path), encoding='utf-8') as page_file:
        source = page_file.read()
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return ['unparsable: %s' % error]
    defects = []
    module_doc = ast.get_docstring(tree)
    title = module_doc.strip().split('\n')[0].strip() if module_doc else ''
    if not title:
        defects.append('no module docstring')
    elif title.lower().rstrip('.') in PLACEHOLDER_TITLES:
        defects.append('placeholder title: %s' % title)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith('test_') and not ast.get_docstring(node):
            defects.append('undocumented test method: %s' % node.name)
    return defects


def table_reference_packages(tree):
    """Package ids the page addresses through a `package.table` reference"""
    references = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg in TABLE_KEYWORDS and isinstance(keyword.value, ast.Constant):
                references.append(keyword.value.value)
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == 'table'
                and node.args and isinstance(node.args[0], ast.Constant)):
            references.append(node.args[0].value)
    return {reference.split('.')[0] for reference in references
            if isinstance(reference, str) and TABLE_REFERENCE.match(reference)}


def resource_owner_package(resource_path):
    """Package id owning a required resource, None when no package owns it alone

    A resource under `resources/common` is on the search path of every site, and
    one provided by more than one package is satisfied by any of them: neither
    tells the page which package it needs.
    """
    relative_path = '%s.py' % resource_path.replace('/', os.sep)
    if os.path.exists(os.path.join(COMMON_RESOURCES_DIR, relative_path)):
        return None
    owners = {os.path.basename(os.path.dirname(resources_dir))
              for resources_dir in glob.glob(PACKAGE_RESOURCES_GLOB)
              if os.path.exists(os.path.join(resources_dir, relative_path))}
    return owners.pop() if len(owners) == 1 else None


def required_resource_packages(tree):
    """Package ids owning the resources the page mixes in through py_requires"""
    packages = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not any(isinstance(target, ast.Name) and target.id in REQUIRES_ATTRIBUTES
                   for target in node.targets):
            continue
        if not isinstance(node.value.value, str):
            continue
        for requirement in node.value.value.split(','):
            resource_path = requirement.split(':')[0].strip()
            if resource_path:
                packages.add(resource_owner_package(resource_path))
    return packages - {None}


def page_required_packages(page_path):
    """Package ids the page needs mounted to render

    Both channels through which a page names another package: the tables it
    addresses and the components it mixes in through `py_requires`.
    """
    with open(os.path.join(PACKAGES_DIR, page_path), encoding='utf-8') as page_file:
        source = page_file.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return table_reference_packages(tree) | required_resource_packages(tree)


def read_ratchet(ratchet_path):
    """Page paths listed in a ratchet file, comments and blank lines ignored"""
    if not os.path.exists(ratchet_path):
        return set()
    with open(ratchet_path, encoding='utf-8') as ratchet_file:
        lines = [line.strip() for line in ratchet_file]
    return {line for line in lines if line and not line.startswith('#')}


def assert_ratchet(offenders, ratchet_path, what):
    """Fail on any offender outside the ratchet and on any stale ratchet entry"""
    known = read_ratchet(ratchet_path)
    ratchet_name = os.path.basename(ratchet_path)
    regressions = sorted(set(offenders) - known)
    stale = sorted(known - set(offenders))
    messages = []
    if regressions:
        messages.append('%s outside %s:\n%s' % (what, ratchet_name,
                                                '\n'.join('  %s' % r for r in regressions)))
    if stale:
        messages.append('stale entries in %s (no longer %s, remove them):\n%s'
                        % (ratchet_name, what, '\n'.join('  %s' % s for s in stale)))
    assert not messages, '\n\n'.join(messages)
