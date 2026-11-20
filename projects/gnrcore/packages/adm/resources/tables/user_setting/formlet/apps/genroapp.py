from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent

info = {
    "code":'genroapp',
    "caption":"!![en]GenroApp",
    "priority":0,
}

PLATFORMS = (('mac', '!![en]Download for macOS'), ('windows', '!![en]Download for Windows'))


def is_enabled(page):
    platform = page.connection.user_device.split(':')[0]
    return bool(page.site.get_genroapp_download_url(platform)
                or page.site.get_genroapp_rundoc_path())

class Formlet(BaseComponent):
    def flt_main(self, pane):
        # GenroApp exposes window.__TAURI__ to the top window: inside the app
        # the download buttons are useless and stay hidden.
        pane.dataFormula('#WORKSPACE.in_genroapp', '!!(window.top.__TAURI__)', _onBuilt=True)
        box = pane.div(padding='10px')
        box.div('!![en]GenroApp opens this application in its own window, without the browser.',
                margin_bottom='15px')
        buttons = box.div(hidden='^#WORKSPACE.in_genroapp', margin_bottom='15px')
        for platform, label in PLATFORMS:
            download_url = self.site.get_genroapp_download_url(platform)
            if download_url:
                buttons.button(label, action="window.open(url,'_blank');", url=download_url,
                               margin_right='10px')
        if self.application.experimentalFlag('login', 'genroapp_device'):
            self.genroapp_devices(box)

    def genroapp_devices(self, pane):
        pane.div('!![en]Computers registered for the GenroApp login', font_weight='bold',
                 margin_bottom='5px')
        pane.dataRpc('#WORKSPACE.devices', self.genroapp_userDevices, _onBuilt=True,
                     _fired='^#WORKSPACE.reload_devices')
        pane.dataRpc(self.genroapp_revokeDevice, subscribe_genroapp_revokeDevice=True,
                     _onResult='FIRE #WORKSPACE.reload_devices;')
        grid = pane.div(height='200px', position='relative').quickGrid('^#WORKSPACE.devices')
        grid.column('device_name', name='!![en]Computer', width='100%')
        grid.column('platform', name='!![en]Platform', width='7em')
        grid.column('verification', name='!![en]Verification', width='9em')
        grid.column('__ins_ts', name='!![en]Registered', width='10em', dtype='DH')
        grid.column('last_used_ts', name='!![en]Last used', width='10em', dtype='DH')
        grid.column('revoked', name='!![en]Revoked', width='6em', dtype='B')
        grid.column('revoke', name=' ', calculated=True, width='3em',
                    cellClasses='cellbutton',
                    format_buttonclass='delete_row buttonIcon',
                    format_isbutton=True,
                    format_onclick="""var row = this.widget.rowByIndex($1.rowIndex);
                                      if(!row.revoked){
                                          genro.publish('genroapp_revokeDevice',{pkey:row.id});
                                      }""")

    @public_method
    def genroapp_userDevices(self):
        return self.db.table('adm.user_device').userDevices(self.avatar.user_id)

    @public_method
    def genroapp_revokeDevice(self, pkey=None):
        self.db.table('adm.user_device').revokeDevice(pkey, self.avatar.user_id)
        self.db.commit()
