from gnrpkg.adm.app_store_helpers import get_app_links

info = dict(caption = "Mobile App",iconClass= "appstore",priority=2)

def is_enabled(page):
    app_links = get_app_links(page)
    if not app_links:
        return False
    return True