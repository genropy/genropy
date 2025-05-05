import os
import json

from gnr.app import pkglog as logger

class AppStoreLinks(object):
    def __init__(self):
        self.app_store_links = {}
    
    def load_app_links(self, path):
        """
        Loads and caches the JSON configuration from the specified path.
        Returns the configuration as a dictionary if the file exists, otherwise returns False.
        """
        if self.app_store_links:
            return self.app_store_links
        else:
            if path and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        # handle bad file content, even if it exists.
                        self.app_store_links = json.load(f)
                    except Exception as e:
                        logger.warning("App Store Links file %s parsing problem: %s", path, e)
                        self.app_store_links = {}
                        
            return self.app_store_links

    def get_app_links(self, page):
        """
        Retrieves the application store links configuration for the given page.
        """
        mainpackage = page.db.application.site.mainpackage
        path = page.getResource('app_store_links.json', pkg=mainpackage)
        return self.load_app_links(path)

    def get_android_link(self, page):
        """
        Returns the Android application link from the configuration.
        Returns False if the configuration is not available or the link is not found.
        """
        return self.get_app_links(page).get("android", False)

    def get_ios_link(self, page):
        """
        Returns the iOS application link from the configuration.
        Returns False if the configuration is not available or the link is not found.
        """
        return self.get_app_links(page).get("ios", False)

app_store_links = AppStoreLinks()

