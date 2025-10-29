# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package               : GenroPy core - see LICENSE for details
# module gnrbagresolver : an advanced data storage system
# Copyright (c)         : 2004 - 2025 Softwell sas - Milano 
# Written by            : Giovanni Porcari, Michele Bertoldi
#                         Saverio Porcari, Francesco Porcari , Francesco Cavazzana
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
import os
import re
import urllib.request
from datetime import datetime, timedelta

import requests

from gnr.core import gnrstring
from gnr.core import logger
from gnr.core.gnrclasses import GnrClassCatalog

class BagResolver(object):
    """BagResolver is an abstract class, that defines the interface for a new kind
    of dynamic objects. By "Dynamic" property we mean a property that is calculated
    in real-time but looks like a static one"""
    classKwargs = {'cacheTime': 0, 'readOnly': True}
    classArgs = []

    def __init__(self, *args, **kwargs):
        self._initArgs = list(args)
        self._initKwargs = dict(kwargs)
        self.parentNode = None
        self.kwargs = {}
        classKwargs = dict(self.classKwargs)
        for j, arg in enumerate(args):
            parname = self.classArgs[j]
            setattr(self, parname, arg)
            classKwargs.pop(parname, None)
            kwargs.pop(parname, None)

        for parname, dflt in list(classKwargs.items()):
            setattr(self, parname, kwargs.pop(parname, dflt))
        self.kwargs.update(kwargs)

        self._attachKwargs()

        self._attributes = {}# ma servono ?????
        self.init()

    def __eq__(self, other):
        try:
            if isinstance(other, self.__class__) and (self.kwargs == other.kwargs):
                return True
        except:
            return False

    def _get_parentNode(self):
        if hasattr(self,'_parentNode'):
            return self._parentNode
            #return self._parentNode()

    def _set_parentNode(self, parentNode):
        if parentNode == None:
            self._parentNode = None
        else:
            #self._parentNode = weakref.ref(parentNode)
            self._parentNode = parentNode

    parentNode = property(_get_parentNode, _set_parentNode)

    def _get_instanceKwargs(self):
        result = {}
        for par, dflt in list(self.classKwargs.items()):
            result[par] = getattr(self, par)
        for par in self.classArgs:
            result[par] = getattr(self, par)
        return result

    instanceKwargs = property(_get_instanceKwargs)

    def _attachKwargs(self):
        for k, v in list(self.kwargs.items()):
            setattr(self, k, v)
            if k in self.classKwargs:
                self.kwargs.pop(k)

    def _set_cacheTime(self, cacheTime):
        self._cacheTime = cacheTime
        if cacheTime != 0:
            if cacheTime < 0:
                self._cacheTimeDelta = timedelta.max
            else:
                self._cacheTimeDelta = timedelta(0, cacheTime)
            self._cache = None
            self._cacheLastUpdate = datetime.min

    def _get_cacheTime(self):
        return self._cacheTime

    cacheTime = property(_get_cacheTime, _set_cacheTime)

    def reset(self):
        """TODO"""
        self._cache = None
        self._cacheLastUpdate = datetime.min

    def _get_expired(self):
        if self._cacheTime == 0 or self._cacheLastUpdate == datetime.min:
            return True
        return ((datetime.now() - self._cacheLastUpdate ) > self._cacheTimeDelta)

    expired = property(_get_expired)

    def __call__(self, **kwargs):
        if kwargs and kwargs != self.kwargs:
            self.kwargs.update(kwargs)
            self._attachKwargs()
            self.reset()

        if self.cacheTime == 0:
            return self.load()

        if self.expired:
            result = self.load()
            self._cacheLastUpdate = datetime.now()
            self._cache = result
        else:
            result = self._cache
        return result

    def load(self):
        """.. warning:: deprecated since version 0.7"""
        pass

    def init(self):
        """TODO
        """
        pass

    def resolverSerialize(self,args=None,kwargs=None):
        """TODO"""
        attr = {}
        attr['resolverclass'] = self.__class__.__name__
        attr['resolvermodule'] = self.__class__.__module__
        attr['args'] = self._initArgs
        attr['kwargs'] = self._initKwargs
        attr['kwargs']['cacheTime'] = self.cacheTime
        return attr
        
    def __getitem__(self, k):
        return self().__getitem__(k)
        
    def _htraverse(self, *args, **kwargs):
        return self()._htraverse(*args, **kwargs)
        
    def getNode(self,k):
        """same method of the dict :meth:`items()`"""
        return self().getNode(k)

    def keys(self):
        """same method of the dict :meth:`keys()`"""
        return list(self().keys())
        
    def items(self):
        """same method of the dict :meth:`items()`"""
        return list(self().items())
        
    def values(self):
        """same method of the dict :meth:`values()`"""
        return list(self().values())
        
    def digest(self, k=None):
        """same method of the dict :meth:`digest()`"""
        return self().digest(k)
        
    def sum(self, k=None):
        """TODO"""
        return self().sum(k)
        
    def iterkeys(self):
        """TODO"""
        return iter(self().keys())
        
    def iteritems(self):
        """TODO"""
        return iter(self().items())

    def itervalues(self):
        """TODO"""
        return iter(self().values())
        
    def __iter__(self):
        return self().__iter__()
        
    def __contains__(self,what):
        return self().__contains__(what)
        
    def __len__(self):
        return len(self())
        
    def getAttributes(self):
        """TODO"""
        return self._attributes
        
    def setAttributes(self, attributes):
        """TODO"""
        self._attributes = attributes or dict()
        
    attributes = property(getAttributes, setAttributes)
        
    def resolverDescription(self):
        """TODO"""
        return repr(self)
        
    def __str__(self):
        return self.resolverDescription()
        


class BagCbResolver(BagResolver):
    """A standard resolver. Call a callback method, passing its kwargs parameters"""
    classArgs = ['method']
        
    def load(self):
        """TODO"""
        return self.method(**self.kwargs)
        
class UrlResolver(BagResolver):
    """TODO"""
    classKwargs = {'cacheTime': 300, 'readOnly': True}
    classArgs = ['url']
        
    def load(self):
        """TODO"""
        x = urllib.request.urlopen(self.url)
        result = {}
        result['data'] = x.read()
        result['info'] = x.info()
        return result

class NetBag(BagResolver):
    classKwargs = {'cacheTime': 300, 'readOnly': True}
    classArgs = ['url','method'] 

    def init(self):

        self.requests = requests
        self.converter = GnrClassCatalog()

    def load(self):
        from gnr.core.gnrbag import Bag
        try:
            params = {k:self.converter.asTypedText(v) for k,v in list(self.kwargs.items())}
            response = self.requests.post('%s/%s' %(self.url,self.method),data=params)
            return Bag(response.text)
        except Exception as e:
            return Bag(dict(error=str(e)))
        
        
class DirectoryResolver(BagResolver):
    """TODO"""
    classKwargs = {'cacheTime': 500,
                   'readOnly': True,
                   'invisible': False,
                   'relocate': '',
                   # FIXME: intercept #file# - emacs' jnl
                   'ext': 'xml',
                   'include': '',
                   'exclude': '',
                   'callback': None,
                   'dropext': False,
                   'processors': None
    }
    classArgs = ['path', 'relocate']
    
    def load(self):
        """TODO"""
        from gnr.core.gnrbag import Bag
        extensions = dict([((ext.split(':') + (ext.split(':'))))[0:2] for ext in self.ext.split(',')]) if self.ext else dict()
        extensions['directory'] = 'directory'
        result = Bag()
        try:
            directory = sorted(os.listdir(self.path))
        except OSError:
            directory = []
        if not self.invisible:
            directory = [x for x in directory if not x.startswith('.')]
        for fname in directory:
            # skip journal files
            if fname.startswith("#") or fname.endswith("#") or fname.endswith("~"):
                logger.debug("Skipping invalid filename %s", fname)
                continue
            nodecaption = fname
            fullpath = os.path.join(self.path, fname)
            relpath = os.path.join(self.relocate, fname)
            addIt = True
            if os.path.isdir(fullpath):
                ext = 'directory'
                if self.exclude:
                    addIt = gnrstring.filter(fname, exclude=self.exclude, wildcard='*')
            else:
                if self.include or self.exclude:
                    addIt = gnrstring.filter(fname, include=self.include, exclude=self.exclude, wildcard='*')
                fname, ext = os.path.splitext(fname)
                ext = ext[1:]
            if addIt:
                label = self.makeLabel(fname, ext)
                processors = self.processors or {}
                processname = extensions.get(ext.lower(), None)
                handler = processors.get(processname)
                if handler is not False:
                    handler = handler or getattr(self, 'processor_%s' % extensions.get(ext.lower(), 'None'), None)
                handler = handler or self.processor_default
                try:
                    stat = os.stat(fullpath)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    atime = datetime.fromtimestamp(stat.st_atime)
                    ctime = datetime.fromtimestamp(stat.st_ctime)
                    size = stat.st_size
                except OSError:
                    mtime = None   
                    ctime = None  
                    atime = None                   
                    size = None
                caption = fname.replace('_',' ').strip()
                m=re.match(r'(\d+) (.*)',caption)
                caption = '!!%s %s' % (str(int(m.group(1))),m.group(2).capitalize()) if m else caption.capitalize()
                nodeattr = dict(file_name=fname, file_ext=ext, rel_path=relpath,
                               abs_path=fullpath, mtime=mtime, atime=atime, ctime=ctime, nodecaption=nodecaption,
                               caption=caption,size=size)
                if self.callback:
                    cbres = self.callback(nodeattr=nodeattr)
                    if cbres is False:
                        continue
                result.setItem(label, handler(fullpath) ,**nodeattr)
        return result
        
    def makeLabel(self, name, ext):
        """TODO
        
        :param name: TODO
        :param ext: TODO"""
        if ext != 'directory' and not self.dropext:
            name = '%s_%s' % (name, ext)
        return name.replace('.', '_')
        
    def processor_directory(self, path):
        """TODO
        
        :param path: TODO"""
        return DirectoryResolver(path, os.path.join(self.relocate, os.path.basename(path)), **self.instanceKwargs)
        
    def processor_xml(self, path):
        """TODO
        
        :param path: TODO"""
        kwargs = dict(self.instanceKwargs)
        kwargs['path'] = path
        return XmlDocResolver(**kwargs)

    processor_xsd = processor_xml

    processor_html = processor_xml

        
    def processor_txt(self, path):
        """TODO
        
        :param path: TODO"""
        kwargs = dict(self.instanceKwargs)
        kwargs['path'] = path
        return TxtDocResolver(**kwargs)
        
    def processor_default(self, path):
        """TODO
        
        :param path: TODO"""
        return None
        
class TxtDocResolver(BagResolver):
    classKwargs = {'cacheTime': 500,
                   'readOnly': True
    }
    classArgs = ['path']
        
    def load(self):
        with open(self.path, mode='rb') as f:
            result = f.read()
        return result

class XmlDocResolver(BagResolver):
    classKwargs = {'cacheTime': 500,
                   'readOnly': True
    }
    classArgs = ['path']

    def load(self):
        from gnr.core.gnrbag import Bag
        return Bag(self.path)


class BagFormula(BagResolver):
    """Calculate the value of an algebric espression"""
    classKwargs = {'cacheTime': 0,
                   'formula': '',
                   'parameters': None, 'readOnly': True
    }
    classArgs = ['formula', 'parameters']
        
    def init(self):
        """TODO"""
        parameters = {}
        for key, value in list(self.parameters.items()):
            if key.startswith('_'):
                parameters[key] = "curr.getResolver('%s')" % value
            else:
                parameters[key] = "curr['%s']" % value
        self.expression = gnrstring.templateReplace(self.formula, parameters)
        
    def load(self):
        """TODO"""
        curr = self.parentNode.parentbag
        return eval(self.expression)



class TraceBackResolver(BagResolver):
    classKwargs = {'cacheTime': 0, 'limit': None}
    classArgs = []

    def load(self):
        import sys, linecache
        from gnr.core.gnrbag import Bag
        result = Bag()
        limit = self.limit
        if limit is None:
            if hasattr(sys, 'tracebacklimit'):
                limit = sys.tracebacklimit
        n = 0
        tb = sys.exc_info()[2]
        while tb is not None and (limit is None or n < limit):
            tb_bag = Bag()

            f = tb.tb_frame
            lineno = tb.tb_lineno
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno)
            if line: line = line.strip()
            else: line = None
            tb_bag['module'] = os.path.basename(os.path.splitext(filename)[0])
            tb_bag['filename'] = filename
            tb_bag['lineno'] = lineno
            tb_bag['name'] = name
            tb_bag['line'] = line
            tb_bag['locals'] = Bag({k:str(v) for k,v in f.f_locals.items()})
            tb = tb.tb_next
            n = n + 1
            result['%s method: %s line: %s' % (tb_bag['module'], name, lineno)] = tb_bag
        return result
