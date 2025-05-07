from gnrpkg.adm.app_store_helpers import app_store_links

info = dict(caption = "Mobile App",iconClass= "appstore",priority=2)

def is_enabled(page):
    app_links = app_store_links.get_app_store_info(page)
    if not app_links:
        return False
    return True
