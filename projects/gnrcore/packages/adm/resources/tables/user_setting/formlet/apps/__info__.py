from gnr.web.gnrgenroapp import connector_config

info = {
    "caption":"!![en]Apps",
    "iconClass":"appstore",
    "priority":4
}

def is_enabled(page):
    platform = page.connection.user_device.split(':')[0]
    return bool(page.site.get_genroapp_download_url(platform)
                or connector_config(page.application))
