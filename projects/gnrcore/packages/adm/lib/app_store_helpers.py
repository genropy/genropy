import os
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def load_app_links(path):
    """
    Loads and caches the JSON configuration from the specified path.
    Returns the configuration as a dictionary if the file exists, otherwise returns False.
    """
    if path and os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return False

def get_app_links(page):
    """
    Retrieves the application store links configuration for the given page.
    """
    mainpackage = page.db.application.site.mainpackage
    path = page.getResource('app_store_links.json', pkg=mainpackage)
    return load_app_links(path)

def get_android_link(page):
    """
    Returns the Android application link from the configuration.
    Returns False if the configuration is not available or the link is not found.
    """
    conf = get_app_links(page)
    if not conf:
        return False
    return conf.get('android') or False

def get_ios_link(page):
    """
    Returns the iOS application link from the configuration.
    Returns False if the configuration is not available or the link is not found.
    """
    conf = get_app_links(page)
    if not conf:
        return False
    return conf.get('ios') or False