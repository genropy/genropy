
info = dict(caption = "Mobile App",iconClass= "appstore",priority=2)

def is_enabled(page):
    if not (page.application.config['mobile_app.android?store_url'] or page.application.config['mobile_app.ios?store_url']):
        return False
    return True
