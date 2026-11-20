from gnr.web.gnrbaseclasses import BaseComponent

info = {
    "code":'genroapp',
    "caption":"!![en]GenroApp",
    "priority":0,
}

def is_enabled(page):
    platform = page.connection.user_device.split(':')[0]
    return bool(page.site.get_genroapp_download_url(platform)
                or page.site.get_genroapp_rundoc_path())

class Formlet(BaseComponent):
    def flt_main(self, pane):
        platform = self.connection.user_device.split(':')[0]
        download_url = self.site.get_genroapp_download_url(platform)
        rundoc_path = self.site.get_genroapp_rundoc_path()
        # GenroApp exposes window.__TAURI__ to the top window: inside the app
        # the download link is useless and stays hidden.
        pane.dataFormula('#WORKSPACE.in_genroapp', '!!(window.top.__TAURI__)', _onBuilt=True)
        box = pane.div(padding='10px')
        box.div('!![en]GenroApp opens this application in its own window, without the browser.',
                margin_bottom='15px')
        if download_url:
            box.div(hidden='^#WORKSPACE.in_genroapp', margin_bottom='10px').a(
                    '!![en]Download GenroApp', href=download_url, target='_blank')
        if rundoc_path:
            box.div(margin_bottom='5px').a('!![en]Download the connection file',
                                           href=f'{self.site.home_uri}_tools/rundoc')
            box.div('!![en]Open the downloaded file with GenroApp to add this application.',
                    font_size='.9em', opacity='.7')
