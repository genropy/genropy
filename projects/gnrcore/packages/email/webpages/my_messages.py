#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


class GnrCustomWebPage(object):
    py_requires = """th/th:TableHandler"""
    
    def main(self, root,**kwargs):
        root.contentPane(region='center', datapath='main').dialogTableHandler(
                                    table='email.message', 
                                    condition__onStart=True,
                                    viewResource='ViewMobile', formResource='FormMobile',
                                    mobileTemplateGrid=True,    
                                    configurable=False,roundedEnvelope=True,
                                    dialog_fullScreen=True,
                                    searchOn=True, addrow=False, delrow=False,
                                    **kwargs)