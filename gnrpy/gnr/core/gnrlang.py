# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrlang : support funtions
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


import sys, traceback, datetime
import importlib
import os.path
import _thread
import uuid
import base64
from types import MethodType
from io import IOBase

from gnr.core.gnrdecorator import deprecated,extract_kwargs # keep for compatibility

try:
    file_types = (file, IOBase)
except NameError:
    file_types = (IOBase,)

thread_ws = dict()
_mixincount = 0

from functools import total_ordering
import time

@total_ordering
class MinType(object):
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return (self is other)

MinValue = MinType()

def getmixincount():
    global _mixincount
    _mixincount+=1
    return '%015i' %_mixincount

def tracebackBag(limit=None):
    import linecache
    from gnr.core.gnrstructures import GnrStructData
    from gnr.core.gnrbag import Bag
    result = Bag()
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
        #tb_bag['locals'] = Bag(f.f_locals.items())
        loc = Bag()
        for k,v in list(f.f_locals.items()):
            try:
                if isinstance(v,GnrStructData):
                    v = '*STRUCTURE*'
                elif isinstance(v,Bag):
                    v = '*BAG*'
                loc[k] = v
            except Exception:
                loc[k] = '*UNSERIALIZABLE* %s' %v.__class__
        tb_bag['locals'] = loc
        tb = tb.tb_next
        n = n + 1
        result['%s method %s line %s' % (tb_bag['module'], name, lineno)] = tb_bag
    return Bag(root=result)


class BaseProxy(object):
    def __init__(self, main):
        self.main=main

class FilterList(list):
    """TODO"""
    
    def __contains__old(self, item):
        return len([k for k in self if k == item or k.endswith('*') and item.startswith(k[0:-1])]) > 0

    def __contains__(self, item):
        # FIXME: if an element of the list is not a string will lead to AttributeError
        for my_item in self:
            if my_item == item or my_item.endswith('*') and item.startswith(my_item[0:-1]):
                return True
        return False

def thlocal():
    """TODO"""
    return thread_ws.setdefault(_thread.get_ident(), {})

def boolean(x):
    """Control if a string is "True" or "False" respect to Genro acceptable "True" and "False" strings
    and return ``True`` (or ``False``). The control is executed on the string uppercased

    * "True" strings: ``TRUE``, ``T``, ``Y``, ``YES``, ``1``
    * "False" strings: ``FALSE``, ``F``, ``N``, ``NO``, ``0``

    :param x: the string to be checked"""
    if isinstance(x, str):
        x = x.upper()
        if x in ('TRUE', 'T', 'Y', 'YES', '1'):
            return True
        if x in ('FALSE', 'F', 'N', 'NO', '0'):
            return False
    return bool(x)

def objectExtract(myobj, f,slicePrefix=True):
    """TODO

    :param myobj: TODO
    :param f: TODO"""
    lf = len(f)
    return dict([(k[lf:] if slicePrefix else k, getattr(myobj, k)) for k in dir(myobj) if k.startswith(f)])

def importModule(module):
    """TODO

    :param module: the module to be imported"""
    if module not in sys.modules:
        __import__(module)
    return sys.modules[module]

def getUuid():
    """Return a Python Universally Unique IDentifier 3 (UUID3) through the Python \'base64.urlsafe_b64encode\' method"""
    t_id = _thread.get_ident()
    t_id = str(t_id)
    uuid_to_encode = uuid.uuid3(uuid.uuid1(), t_id).bytes
    return base64.urlsafe_b64encode(uuid_to_encode)[0:22].replace(b'-', b'_').decode()

def safe_dict(d):
    """Use the str method, coercing all the dict keys into a string type and return the dict
    with string-type keys

    :param d: a dict"""
    return dict([(str(k), v) for k, v in list(d.items())])

def position(v, list_or_string):
    try:
        return list_or_string.index(v)
    except ValueError:
        return -1

def uniquify(seq):
    """TODO

    :param seq: TODO"""
    def seen_function(seq):
        seen = set()
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            yield x

    return list(seen_function(seq))

def optArgs(**kwargs):
    """TODO"""
    return dict([(k, v) for k, v in list(kwargs.items()) if v != None])

def moduleDict(module, proplist):
    """TODO

    :param module: TODO
    :param proplist: TODO"""
    result = {}
    if isinstance(module, str):
        module = gnrImport(module)
    for prop in [x.strip() for x in proplist.split(',')]:
        modulelist = [getattr(module, x) for x in dir(module) if
                      hasattr(getattr(module, x), prop) and getattr(getattr(module, x), '__module__',
                                                                    None) == module.__name__]
        result.update(dict([(getattr(x, prop).lower(), x) for x in modulelist]))
    return result

def gnrImport(source, importAs=None, avoidDup=False, silent=True,avoid_module_cache=None):
    modkey = source
    path_sep = os.path.sep
    if path_sep in source:
        if avoidDup and not importAs:
            importAs = os.path.splitext(source)[0].replace(path_sep, '_').replace('.', '_')
        modkey = importAs or os.path.splitext(os.path.basename(source))[0]
    else:
        module = importlib.import_module(source)
        if importAs:
            sys.modules[importAs] = module
        return module
    if not avoid_module_cache:
        try:
            m = sys.modules[modkey]
            return m
        except KeyError:
            pass
    silent =False
    spec = importlib.util.spec_from_file_location(modkey, source)
    if not spec:
        return
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except SyntaxError:
        raise
    except ImportError:
        raise
    except Exception:
        if not silent:
            raise
        module = None
    sys.modules[modkey] = module
    return module

class GnrException(Exception):
    """Standard Gnr Exception"""
    code = 'GNR-001'
    description = '!!Genro base exception'
    caption = """!!Error code %(code)s : %(description)s."""
    localizer = None

    def __init__(self, description=None, localizer=None,**kwargs):
        if not description:
            import inspect
            st = inspect.stack()
            description = "%s:%i"%(st[1][1],st[1][2])
        self.description = description
        # FIXME: why a localizer param saved as attribute
        # and immediately discarded?
        self.localizer = localizer
        self.msgargs = kwargs
        self.localizer = None

    def __str__(self):
        msgargs = dict(code=self.code, description=self.description)
        if hasattr(self,'msgargs'):
            msgargs.update(self.msgargs)
        return self.localizedMsg(self.caption, msgargs)

    def setLocalizer(self, localizer):
        """TODO

        :param localizer: TODO"""
        self.localizer = localizer

    def localize(self, v):
        """TODO

        :param v: TODO"""
        return self.localizer.translate(v)

    def localizedMsg(self, msg, msgargs):
        """TODO

        :param msg: TODO
        :param msgargs: TODO"""
        if self.localizer:
            msg = self.localize(msg)
            for k, v in list(msgargs.items()):
                if isinstance(v, str) and v.startswith('!!'):
                    msgargs[k] = self.localize(msgargs[k])
        return msg % msgargs % msgargs # msgargs is use 2 times as we could have msgargs nested(max 1 level)

class GnrSilentException(GnrException):
    def __init__(self, topic=None,**kwargs):
        self.topic = topic
        self.parameters = kwargs

class GnrDebugException(GnrException):
    pass

class NotImplementedException(GnrException):
    pass

class MandatoryException(GnrException):
    pass

class GnrObject(object):
    """TODO"""
    def __init__(self):
        pass

    def mixin(self, cls, **kwargs):
        """TODO

        :param cls: the python class to mixin"""
        if isinstance(cls, str):
            drive, cls = os.path.splitdrive(cls)
            modulename, cls = cls.split(':')
            modulename = '%s%s'%(drive, modulename)
            m = gnrImport(modulename)
            if m != None:
                cls = getattr(m, cls)
            else:
                raise GnrException('cannot import module: %s' % modulename)
        return instanceMixin(self, cls, **kwargs)

def args(*args, **kwargs):
    """TODO"""
    return (args, kwargs)

def cloneClass(name, source_class):
    """TODO

    :param name: TODO
    :param source_class: TODO"""
    return type(name, source_class.__bases__, dict([(k, v) for k, v in list(source_class.__dict__.items())
                                                    if not k in ('__dict__', '__module__', '__weakref__', '__doc__')]))

def moduleClasses(m):
    """TODO

    :param m: TODO"""
    modulename = m.__name__
    return [x for x in dir(m) if (not x.startswith('__')) and  getattr(getattr(m, x), '__module__', None) == modulename]

def clonedClassMixin(target_class, source_class, methods=None, only_callables=True,
               exclude='js_requires,css_requires,py_requires',**kwargs):
    target_class = cloneClass('CustomResource', target_class)
    classMixin(target_class,source_class,methods=methods,only_callables=only_callables,exclude=exclude,
                **kwargs)
    return target_class

def classMixin(target_class, source_class, methods=None, only_callables=True,
               exclude='js_requires,css_requires,py_requires',**kwargs):
    """Add to the class methods from 'source'.

    :param target_class: TODO
    :param source_class: TODO
    :param methods: TODO
    :param only_callables: TODO
    :param exclude: TODO. If not *methods* then all methods are added"""

    if isinstance(methods, str):
        methods = methods.split(',')
    if isinstance(exclude, str):
        exclude = exclude.split(',')
    if isinstance(source_class, str):
        drive, source_class = os.path.splitdrive(source_class)
        asProxy = None
        if ' AS ' in source_class:
            source_class,asProxy = map(lambda r: r.strip(),source_class.split(' AS '))
        if ':' in source_class:
            modulename, clsname = source_class.split(':')
        else:
            modulename, clsname = source_class, '*'
        modulename = '%s%s'%(drive, modulename)
        m = gnrImport(modulename, avoidDup=True)
        if m is None:
            raise GnrException('cannot import module: %s' % modulename)
        if clsname == '*':
            classes = moduleClasses(m)
        else:
            classes = [clsname]
        for clsname in classes:
            source_class = getattr(m, clsname, None)
            if asProxy:
                if not hasattr(source_class,'is_proxy'):
                    raise GnrException('{} is not a proxy'.format(clsname))
                source_class.proxy_name = asProxy
            if source_class:
                classMixin(target_class, source_class, methods=methods,
                            only_callables=only_callables, exclude=exclude,
                            **kwargs)
        return
    if source_class is None:
        return
    if hasattr(source_class, '__py_requires__'):
        py_requires_iterator = source_class.__py_requires__(target_class, **kwargs)
        for cls_address in py_requires_iterator:
            classMixin(target_class, cls_address, methods=methods,
                       only_callables=only_callables, exclude=exclude,
                       **kwargs)
    exclude_list = dir(type) + ['__weakref__', '__onmixin__', '__on_class_mixin__', '__py_requires__','proxy']
    if exclude:
        exclude_list.extend(exclude)
    mlist = [k for k in dir(source_class) if
             ((only_callables and callable(getattr(source_class, k))) or not only_callables) and not k in exclude_list]
    if methods:
        mlist = [item for item in mlist if item in FilterList(methods)]
    if exclude:
        mlist = [item for item in mlist if item not in FilterList(exclude)]
    proxy_name = getattr(source_class, 'proxy_name', None)
    if proxy_name:
        keyproxy = '{proxy_name}_proxyclass'.format(proxy_name=proxy_name)
        proxy_class =  getattr(target_class, keyproxy, None)
        if not proxy_class:
            proxy_class = getattr(target_class,'proxy_class',BaseProxy)
            proxy_class = cloneClass('CustomProxy', proxy_class)
           # proxy_inherites = getattr(source_class,'proxy_inherites',None)
           # if proxy_inherites:
           #     for parent_proxy in proxy_inherites.split(','):
           #         classMixin(proxy_class,parent_proxy)
            setattr(target_class,keyproxy,proxy_class)
        target_class = proxy_class
    __mixin_pkg = getattr(source_class, '__mixin_pkg', None)
    __mixin_path = getattr(source_class, '__mixin_path', None)
    for name in mlist:
        original = target_class.__dict__.get(name)

        base_generator = base_visitor(source_class)
        new = None
        found = False
        while not found:
            base_class = next(base_generator)
            if name in base_class.__dict__:
                new = base_class.__dict__.get(name)
                found = True
        if callable(new):
            new.proxy_name = proxy_name
            new.__mixin_pkg = __mixin_pkg
            new.__mixin_path = __mixin_path
        if getattr(new,'mixin_as',None):
            if '#' in new.mixin_as:
                id_new = str(id(new))
                mixin_as = new.mixin_as.replace('#',id_new)
                if not hasattr(target_class,mixin_as):
                    new.__order = getmixincount()
                    setattr(target_class, mixin_as, new)
            else:
                setattr(target_class, mixin_as, new)
        else:
            setattr(target_class, name, new)
            if original:
                setattr(target_class, '%s_' % name, original)
    if hasattr(source_class, '__on_class_mixin__'):
        source_class.__on_class_mixin__(target_class, **kwargs)

def base_visitor(cls):
    """TODO

    :param cls: TODO"""
    yield cls
    for base in cls.__bases__:
        for inner_base in base_visitor(base):
            yield inner_base

def serializedFuncName(func, cls=None):
    funcName = func.__name__
    if funcName.startswith('rpc_'):
        funcName = funcName[4:]
    proxy_name=getattr(func, 'proxy_name', None)
    cls = cls or func.__self__.__class__
    _gnrPublicName = getattr(cls,'_gnrPublicName',None)
    if _gnrPublicName:
        proxy_name = _gnrPublicName
    if cls.__name__=='SqlTable':
        proxy_name = "_table.%s" % func.__self__.fullname
    if proxy_name:
        funcName = '%s.%s'%(proxy_name,funcName)
    __mixin_pkg = getattr(func, '__mixin_pkg', None)
    __mixin_path = getattr(func, '__mixin_path', None)
    is_websocket = getattr(func, 'is_websocket',None)
    if __mixin_path:
        if not __mixin_pkg:
            __mixin_pkg='*'
        funcName = '%s|%s;%s'%(__mixin_pkg, __mixin_path, funcName)
    if is_websocket:
        funcName =funcName
    return funcName

@extract_kwargs(mangling=True)
def instanceMixin(obj, source, methods=None, attributes=None, only_callables=True,
                  exclude='js_requires,css_requires,py_requires',
                  prefix=None, suffix=None, mangling_kwargs=None,_mixined=None,**kwargs):
    """Add to the instance obj methods from 'source'

    ``instanceMixin()`` method is decorated with the :meth:`extract_kwargs <gnr.core.gnrdecorator.extract_kwargs>` decorator

    :param obj: TODO
    :param source: it can be an instance or a class
    :param methods: If ``None``, then all methods are added
    :param attributes: TODO
    :param only_callables: boolean. TODO
    :param exclude: TODO
    :param prefix: TODO
    :param mangling_kwargs: TODO"""

    if _mixined is None:
        _mixined=[]
    if isinstance(methods, str):
        methods = methods.split(',')
    if isinstance(exclude, str):
        exclude = exclude.split(',')
    exclude = exclude or ''
    if isinstance(source, str):
        drive, source = os.path.splitdrive(source)
        if ':' in source:
            modulename, clsname = source.split(':')
        else:
            modulename, clsname = source, '*'
        modulename = '%s%s'%(drive, modulename)
        m = gnrImport(modulename, avoidDup=True)
        if m is None:
            raise GnrException('cannot import module: %s' % modulename)
        if clsname == '*':
            classes = moduleClasses(m)
        else:
            classes = [clsname]
        for clsname in classes:
            source = getattr(m, clsname, None)
            if source:
                instanceMixin(obj, source, methods=methods, only_callables=only_callables, exclude=exclude,
                         prefix=prefix, suffix=suffix,_mixined=_mixined, **kwargs)
        return _mixined
    if source is None:
        return
    source_dir = dir(source)
    proxies = {k:getattr(source, k) for k in source_dir if k.endswith('_proxyclass')}
    blacklist = dir(type) + \
                ['__weakref__', '__onmixin__','mixin','proxy_class','proxy_class_'] + \
                list(proxies.keys())
    mlist = [k for k in source_dir if callable(getattr(source, k)) and not k in blacklist]
    if methods:
        mlist = [item for item in mlist if item in FilterList(methods)]
    if exclude:
        mlist = [item for item in mlist if item not in FilterList(exclude)]
    __mixin_pkg = getattr(source, '__mixin_pkg', None)
    __mixin_path = getattr(source, '__mixin_path', None)
    for k,proxyclass in proxies.items():
        for mname in dir(proxyclass):
            proxyitem = getattr(proxyclass,mname)
            if callable(proxyitem) and mname not in dir(type)+['__weakref__', '__onmixin__','mixin','proxy_class','proxy_class_']:
                method = proxyitem
                method.__mixin_pkg = __mixin_pkg
                method.__mixin_path = __mixin_path
        setattr(obj,k.replace('_proxyclass',''),proxyclass(obj))
    for name in mlist:
        method = getattr(source, name)
        if type(method) == MethodType:
            method = method.__func__
        k = MethodType(method, obj)

        #method = getattr(source, name).__func__
        method.__mixin_pkg = __mixin_pkg
        method.__mixin_path = __mixin_path
        #k = instmethod(method, obj, obj.__class__)
        curr_prefix = prefix
        name_as =getattr(method,'instance_mixin_as',name)
        if mangling_kwargs and '_' in name:
            splitted_name=name.split('_',1)
            mangling = mangling_kwargs.get(splitted_name[0],None)
            if mangling:
                curr_prefix=mangling
                name=splitted_name[1]
        if curr_prefix:
            name_as = '%s_%s' % (curr_prefix, name)
        if suffix:
            name_as = '%s_%s' % (name_as, suffix)
        if hasattr(obj, name_as):
            original = getattr(obj, name_as)
            setattr(obj, name_as + '_', original)
        setattr(obj, name_as, k)
        _mixined.append(name_as)
    if not only_callables:
        attributes = [k for k in source_dir if
                      not callable(getattr(source, k)) and not k.startswith('_') and not k in exclude]
    if attributes:
        if isinstance(attributes, str):
            attributes = attributes.split(',')
        for attribute in attributes:
            if hasattr(source, attribute):
                setattr(obj, attribute, getattr(source, attribute))
    if hasattr(source, '__onmixin__'):
        source.__onmixin__.__func__(obj, _mixinsource=source, **kwargs)
    return _mixined

def safeStr(self, o):
    """Return a safe string

    :param o: the string to be checked"""
    if isinstance(o, str):
        return o.encode('UTF-8', 'ignore')
    else:
        return str(o)

#def checkGarbage():
#    gc.collect()
#    assert not gc.garbage

def instanceOf(obj, *args, **kwargs):
    """TODO

    :param obj: TODO"""
    if isinstance(obj, str):
        drive, obj = os.path.splitdrive(obj)
        modulename, clsname = obj.split(':')
        modulename = '%s%s'%(drive,modulename)
        m = gnrImport(modulename)
        return getattr(m, clsname)(*args, **kwargs)
    elif isinstance(obj, type): # is a class, not an instance
        return obj(*args, **kwargs)
    else:
        return obj

def errorTxt():
    """TODO"""
    el = sys.exc_info()
    tb_text = traceback.format_exc()
    e = el[2]
    while e.tb_next:
        e = e.tb_next

    locals_list = []
    for k, v in list(e.tb_frame.f_locals.items()):
        try:
            from gnr.core.gnrstring import toText
            strvalue = toText(v)
        except:
            strvalue = 'unicode error'
        locals_list.append('%s: %s' % (k, strvalue))
    return u'%s\n\nLOCALS:\n\n%s' % (tb_text, '\n'.join(locals_list))

def errorLog(proc_name, host=None, from_address='', to_address=None, user=None, password=''):
    """Report the error log

    :param proc_name: the name of the wrong process
    :param host: the database server host
    :param from_address: the email sender
    :param to_address: the email receiver
    :param user: the username
    :param password: the username's password"""
    from gnr.utils.gnrmail import sendmail

    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S: ')
    title = '%s - Error in %s' % (ts, proc_name)
    print(title)
    tb_text = errorTxt()
    print(tb_text.encode('ascii', 'ignore'))

    if (host and to_address):
        try:
            sendmail(host=host,
                     from_address=from_address,
                     to_address=to_address,
                     subject=title,
                     body=tb_text,
                     user=user,
                     password=password
                     )
        except:
            pass
    return tb_text

if __name__ == '__main__':
    pass
