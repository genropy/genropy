# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrbag : an advanced data storage system
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

import os.path

from gnr.core.gnrbag import Bag
from gnr.web import logger

class DojoApiReader(object):
    discard = ['provides', 'resources', 'mixins']
    discard = []

    def __init__(self, apipath, resultpath=None):
        self.resultpath = resultpath or os.path.dirname(apipath)
        self.source = Bag(apipath)['javascript']
        self.apibag = Bag()
        for node in self.source:
            attr = dict(node.attr)
            value = node.value
            location = attr.pop('location')
            if isinstance(value, Bag):
                value = self.convertObject(value)
            if location in self.apibag:
                logger.info('redefining object: %s', location)
            else:
                self.write(location, value, attr)
                self.apibag.setItem(location, value, attr)

    def write(self, location, obj, attr):
        destpath = [self.resultpath, 'objects'] + location.split('.') + 'obj.xml'
        if attr:
            logger.debug(attr)
        destpath = os.path.join(**destpath)
        obj.toXml(destpath, autocreate=True)

    def convertObject(self, src):
        result = Bag()
        for node in src:
            label = node.label
            if label in self.discard:
                continue
            attr = dict(node.attr)
            value = node.value
            if label == 'mixins':
                label = 'mixins_%s' % attr.get('scope', 'undefined_scope')
            if isinstance(value, Bag):
                value = self.convertItems(value)
            if label in result:
                logger.info('redefining: %s', label)
            result.setItem(label, value, attr)
        return result

    def convertItems(self, items):
        result = Bag()
        for k, node in enumerate(items):
            label = node.label
            value = node.value
            attr = dict(node.attr)
            if label == 'method':
                label = attr.get('name')
            if label == 'property':
                label = attr.get('name')
            else:
                label = 'r_%i' % k
            if label:
                result.setItem(label, value, attr)
        return result

