import locale
import os

# Match CI environment (see .github/workflows/tests.yml)
os.environ.setdefault('GNR_LOCALE', 'en_GB')
os.environ.setdefault('LC_ALL', 'en_GB')
os.environ.setdefault('LANG', 'en_GB')

# Ensure Python's locale module returns a valid locale for babel
try:
    locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_GB')
    except locale.Error:
        pass  # keep system default if en_GB is not available
