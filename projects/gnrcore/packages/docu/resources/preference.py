
# # -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

class AppPref(object):
    def permission_docu(self,**kwargs):
        return '_DEV_'

    def prefpane_docu(self, parent,**kwargs): 
        bc = parent.borderContainer(region='center', **kwargs)
        self.mainDocuPreferences(bc.contentPane(region='top'))
        tc = bc.tabContainer(region='center')
        self.handbooksTheme(tc.contentPane(title='!![en]Handbooks theme', datapath='.handbooks_theme'))
        self.baseCss(tc.contentPane(title='!![en]Base CSS'))
        self.baseHtml(tc.contentPane(title='!![en]Base HTML'))
        self.baseJs(tc.contentPane(title='!![en]Base JS'))
        
    def mainDocuPreferences(self, pane):
        fb = pane.formbuilder(cols=1,border_spacing='4px')
        fb.textbox('^.sphinx_baseurl', lbl='!![en]Sphinx baseurl', placeholder='Default: http://genropy.org/docs/')
        fb.textbox('^.cloudfront_distribution_id', lbl='!![en]Cloudfront distribution ID', placeholder='E.g. E350MXXXXXZ73K')
        fb.checkbox('^.manage_redirects', label='!![en]Manage redirects')
        fb.checkbox('^.enable_sitemap', label='!![en]Enable sitemap')
        fb.checkbox('^.save_src_debug', label='!![en]Save source debug files')
        if self.db.package('genrobot'):
            fb.checkBox(value='^.telegram_notification', lbl='', label='Enable Telegram Notification')
            fb.dbselect('^.bot_token', lbl='Default BOT', table='genrobot.bot', columns='$bot_name', alternatePkey='bot_token',
                            colspan=3, hasDownArrow=True, hidden='^.telegram_notification?=!#v')
            
    def handbooksTheme(self, pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.img(src='^.logo', lbl='!![en]Handbook Logo', width='200px', height='100px', 
                            crop_width='200px', crop_height='100px',
                            edit=True, placeholder=True,
                            upload_filename='docu_logo.png',
                            upload_folder='home:documentation/img')
        fb.textbox(value='^.copyright', lbl='!![en]Copyright text')  
        fb.checkbox(value='^.last_update', label='!![en]Show last update date') 
        fb.checkbox(value='^.display_version', label='!![en]Display version number')
        fb.checkbox(value='^.show_authors', label='!![en]Show authors')
    
    def baseCss(self, pane):
        pane.codemirror('^.base_css', height='100%', width='100%',
                            config_lineNumbers=True, config_mode='css')
        
    def baseHtml(self, pane):
        pane.codemirror('^.base_html', height='100%', width='100%',             #DP Todo
                            config_lineNumbers=True, config_mode='html',
                            config_addon='search,lint')
    
    def baseJs(self, pane):
        pane.codemirror('^.base_js', height='100%', width='100%',             #DP Todo
                            config_lineNumbers=True, config_mode='javascript',
                            config_addon='search,lint')
            
class UserPref(object):
    pass