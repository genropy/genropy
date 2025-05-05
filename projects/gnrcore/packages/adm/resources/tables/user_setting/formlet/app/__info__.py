import json
info = dict(caption = "Mobile App",iconClass= "appstore",priority=2)

def is_enabled(page):
    mainpackage = page.db.application.site.mainpackage
    with open(page.getResource('app_store_links.json',pkg=mainpackage), 'r', encoding='utf-8') as f:
        stores_dict = json.loads(f.read())
    if not stores_dict:
        return False