# -*- coding: UTF-8 -*-
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

from gnr.core.gnrdecorator import public_method

class AppPref(object):
    def permission_glbl(self, **kwargs):
        return 'admin'
    def prefpane_glbl(self, parent, **kwargs):
        pane = parent.contentPane(**kwargs)
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.button('Dump GLBL',action="""genro.mainGenroWindow.genro.publish('open_batch');
                                        genro.serverCall('_package.glbl.createStartupData',null,function(){});
                                    """,_tags='_DEV_')
        fb.button('Restore GLBL',action="""genro.mainGenroWindow.genro.publish('open_batch');
                                        genro.serverCall('_package.glbl.loadStartupData',null,function(){});
                                    """,_tags='_DEV_')

