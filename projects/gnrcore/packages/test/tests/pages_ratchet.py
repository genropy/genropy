"""Page discovery and the three ratchet files, shared by the suites that assert on them.

`test_pages_documented.py` and `test_pages_framecodes.py` need nothing but this
module and the source tree; `test_pages_smoke.py` adds a running site to render
every page it finds here.
Keeping the two kinds apart is what lets the source-only ratchets run in CI, where
no instance is built: a check that silently skips is a check that protects nothing.
"""
import ast
import os

PACKAGES = ('test', 'test15')

# titles that render as a page heading but say nothing about the page
PLACEHOLDER_TITLES = ('test page description', 'test', '-', 'index.py', 'test page')

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGES_DIR = os.path.abspath(os.path.join(TESTS_DIR, *[os.pardir] * 2))
SMOKE_RATCHET = os.path.join(TESTS_DIR, 'smoke_known_failures.txt')
DOCSTRING_RATCHET = os.path.join(TESTS_DIR, 'docstring_debt.txt')
FRAMECODE_RATCHET = os.path.join(TESTS_DIR, 'framecode_debt.txt')

SKIP_FOLDERS = ('_resources', '__pycache__')


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


def duplicate_framecodes(source):
    """frameCode literals the given page source uses more than once, sorted

    Only string literals are seen, because only the ast is read: a commented-out
    call builds no frame and raises nothing, and a frameCode built at runtime is
    out of reach. Every collision this migration produced was a literal.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    counts = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != 'frameCode':
                continue
            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                counts[value.value] = counts.get(value.value, 0) + 1
    return sorted(code for code, count in counts.items() if count > 1)


def framecode_collisions(page_path):
    """frameCode values repeated by the page at the given package-relative path"""
    with open(os.path.join(PACKAGES_DIR, page_path), encoding='utf-8') as page_file:
        return duplicate_framecodes(page_file.read())


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
