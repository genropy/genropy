
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
        pane = parent.contentPane(**kwargs)
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox('^.sphinx_path', lbl='!![en]Sphinx project path', placeholder='E.g. documentation:handbooks')
        fb.textbox('^.local_path', lbl='!![en]Local handbooks path', placeholder='E.g. documentation:local_handbooks')
        fb.textbox('^.sphinx_baseurl', lbl='!![en]Sphinx baseurl', placeholder='Default: http://genropy.org/docs/')
        fb.textbox('^.cloudfront_distribution_id', lbl='!![en]Cloudfront distribution ID', placeholder='E.g. E350MXXXXXZ73K')
        fb.checkbox('^.manage_redirects', lbl='', label='!![en]Manage redirects')
        if self.db.package('genrobot'):
            fb.checkBox(value='^.telegram_notification', lbl='', label='Enable Telegram Notification')
            fb.dbselect('^.bot_token', lbl='Default BOT', table='genrobot.bot', columns='$bot_name', alternatePkey='bot_token',
                            colspan=3, hasDownArrow=True, hidden='^.telegram_notification?=!#v')
            
class UserPref(object):
    pass