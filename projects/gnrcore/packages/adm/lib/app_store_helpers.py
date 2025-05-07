class AppStoreLinks(object):
    def __init__(self):
        self.app_store_info = None
    

    def get_app_store_info(self, page):
        """
        Retrieves the application store links configuration for the given page.
        """
        if self.app_store_info is None:
            mobile_app = page.db.application.config['mobile_app']
            self.app_store_info = {n.label:n.attr for n in mobile_app} if mobile_app else {}
        return self.app_store_info

    def get_android(self, page):
        """
        Returns the Android application link from the configuration.
        Returns False if the configuration is not available or the link is not found.
        """
        return self.get_app_store_info(page).get("android", False)

    def get_ios(self, page):
        """
        Returns the iOS application link from the configuration.
        Returns False if the configuration is not available or the link is not found.
        """
        return self.get_app_store_info(page).get("ios", False)

app_store_links = AppStoreLinks()

