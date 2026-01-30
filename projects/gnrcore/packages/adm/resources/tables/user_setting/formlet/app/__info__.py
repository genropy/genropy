
info = dict(caption = "Mobile App",iconClass= "appstore",priority=2)

def is_enabled(page):
    return page.site.is_mobile_app_enabled()
