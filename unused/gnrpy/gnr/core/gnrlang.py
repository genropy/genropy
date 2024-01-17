
class GnrImportedModule(object):
    """TODO"""
    def __init__(self, source):
        if isinstance(source, str):
            self.path = source
            self.name = inspect.getmodulename(source)
            self.module = None
            self.load()
        elif(inspect.ismodule(source)):
            self.module = source
            self.name = source.__name__
            path = source.__file__
            info = inspect.getmoduleinfo(path)
            if info[1] == 'pyc':
                path = os.path.splitext(path)[0] + '.py'
                if os.path.isfile(path):
                    self.path = path
                else:
                    self.path = source.__file__
            else:
                self.path = path

    def getPath(self):
        """Get the path of the module and return it"""
        return self.path

    def getModule(self):
        """Get the module and return it"""
        return self.module

    def getName(self):
        """Get the module name and return it"""
        return self.name

    def getDoc(self, memberName=None):
        """TODO

        :param memberName: TODO"""
        m = self.module
        if memberName:
            m = self.getMember(memberName)
        if m:
            doc = m.__doc__
        if doc: doc = str(doc, 'UTF-8')
        else: doc = ""
        return doc

    def getMember(self, memberName):
        """TODO

        :param memberName: TODO"""
        return getattr(self.module, memberName, None)

    #    def getImportedMember(self, memberName):
    #        return ImportedMember(self, memberName)

    def load(self):
        """TODO"""
        m_name = os.path.basename(self.path).split(".")[0]
        if self.path.endswith('py'):
            script_path = os.path.abspath(self.path)
            self.module = SourceFileLoader(m_name, script_path).load_module()
        else:
            self.module = imp.load_compiled(self.name, self.path)

    def update(self):
        """TODO"""
        self.load()


def addCallable(obj, method):
    """TODO

    :param obj: TODO
    :param method: TODO"""
    name = method.__name__
    setattr(obj, name, method)

def addBoundCallable(obj, method, importAs=None):
    """TODO

    :param obj: TODO
    :param method: TODO
    :param importAs: TODO"""
    z = type(obj.__init__)
    k = z(method, obj, obj.__class__)
    if not importAs:
        importAs = method.__name__
    setattr(obj, importAs, k)

def setMethodFromText(obj, src, importAs):
    """TODO

    :param obj: TODO
    :param src: TODO
    :param importAs: TODO"""
    compiled = compile(src, 'xyz', 'exec')
    auxDict = {}
    exec(compiled, auxDict)
    addBoundCallable(obj, auxDict[importAs], importAs)

def getObjCallables(obj):
    """TODO

    :param obj: TODO"""
    return [(k, getattr(obj, k))  for k in dir(obj) if
            callable(getattr(obj, k)) and not k in ('__call__', '__class__', '__cmp__')]

def getObjAttributes(obj):
    """TODO

    :param obj: TODO"""
    return [(k, getattr(obj, k))  for k in dir(obj) if not callable(getattr(obj, k))]

def callables(obj):
    """TODO

    :param obj: TODO"""
    s = getObjCallables(obj)
    return '\n'.join([x for x, v in s])

def testbound(self, n):
    """TODO

    :param n: TODO"""
    self.special = n * '-'
    return self.special

def compareInstances(a, b, __visited=None):
    """TODO

    :param a: TODO
    :param b: TODO
    """
    if not __visited:
        __visited = {}
    k1 = str(id(a)) + '-' + str(id(b))
    k2 = str(id(b)) + '-' + str(id(a))
    if dir(a) != dir(b):
        return False
    builtins = dir(__builtins__)
    for propName in dir(a):
        prop = getattr(a, propName)
        if not callable(prop):
            if prop.__class__.__name__ in builtins:
                if prop != getattr(b, propName):
                    return False
            else:
                if not k1 in __visited and not k2 in __visited:
                    result = compareInstances(prop, getattr(b, propName))
                    if result:
                        __visited[k1] = None
                    else:
                        return False
    return True

def setCallable(obj, name, argstring=None, func='pass'):
    """TODO

    :param obj: TODO
    :param name: TODO
    :param argstring: TODO
    :param func: TODO"""
    body = '    ' + '\n    '.join(func.split('\n'))
    if argstring:
        argstring = ',' + argstring
    else:
        argstring = ''
    f = "def %s(self%s):\n%s" % (name, argstring, body)
    setMethodFromText(obj, f, name)


class GnrAddOn(object):
    """A class to be subclassed to inherit some introspection methods"""

    def className(self):
        """Get the class name and return it"""
        return self.__class__.__name__

    def recorderReset(self):
        """TODO"""
        self.__recorder__ = []

    def recorderWrite(self):
        """TODO"""
        frame = sys._getframe(1)
        selector = frame.f_code.co_name
        srcargname, srcargs, srckwargs, vlocals = inspect.getargvalues(frame)
        srcdefaults = inspect.getargspec(getattr(self, selector))[3]
        if not srcdefaults: srcdefaults = []
        nargs = len(srcargname) - len(srcdefaults)
        args = [vlocals[key] for key in srcargname[1:nargs]]
        if srcargs: args.extend(vlocals[srcargs])
        kwargs = dict([(key, vlocals[key]) for key in srcargname[nargs:]])
        if  srckwargs: kwargs.update(vlocals[srckwargs])
        self.__recorder__.append((selector, args, kwargs))

    def recorderGet(self):
        """TODO"""
        return self.__recorder__

    def recorderDo(self, recorder=None):
        """TODO

        :param recorder: TODO"""
        if not recorder: recorder = self.__recorder__[:]
        result = []
        for command, args, kwargs in recorder:
            commandHandler = getattr(self, command)
            result.append(commandHandler(*args, **kwargs))
        return result

    def superdo(self, *args, **kwargs):
        """Like calling :meth:`super()` with the right arguments

        ??? check if it works on multiple levels"""
        frame = sys._getframe(1)
        superObj = super(self.__class__, self)
        selector = frame.f_code.co_name
        selectorMethod = getattr(superObj, selector, None)
        if selectorMethod:
            if not(args or kwargs):
                srcargname, srcargs, srckwargs, vlocals = inspect.getargvalues(frame)
                srcdefaults = inspect.getargspec(getattr(self, selector))[3]
                if not srcdefaults: srcdefaults = []
                nargs = len(srcargname) - len(srcdefaults)
                args = [vlocals[key] for key in srcargname[1:nargs]]
                if srcargs: args.extend(vlocals[srcargs])
                kwargs = dict([(key, vlocals[key]) for key in srcargname[nargs:]])
                if  srckwargs: kwargs.update(vlocals[srckwargs])
                dstargname, dstargs, dstkwargs, dstdefaults = inspect.getargspec(selectorMethod)
                if not dstdefaults: dstdefaults = []
                nargs = len(dstargname) - len(dstdefaults) - 1
                if not dstargs: args = args[:nargs]
                if not dstkwargs:
                    dstkw = dstargname[-len(dstdefaults):]
                    kwargs = dict([(key, value) for key, value in list(kwargs.items()) if key in dstkw])
            return selectorMethod(*args, **kwargs)

    dosuper = staticmethod(superdo)

    def setCallable(self, src, importAs=None, bound=True):
        """TODO

        :param src: is a string of a python function or an imported function
        :param importAs: a name for identify the function in error messages
        :param bound: boolean. If ``True`` the function will be bounded to this instance"""
        if isinstance(src, str):
            if not importAs: importAs = 'abcd'
            compiled = compile(src, importAs, 'exec')
            auxDict = {}
            exec(compiled, auxDict)
            for name, obj in list(auxDict.items()):
                self.setCallable(obj, name, bound=bound)
        elif inspect.isfunction(src):
            if not importAs: importAs = src.__name__
            if bound:
                newbounded = type(self.__init__)(src, self, self.__class__)
                setattr(self, importAs, newbounded)
            else:
                setattr(self, importAs, src)

class GnrRemeberableAddOn(GnrAddOn):
    """TODO"""
    _gnr_members__ = {}
    _gnr_namedmembers__ = {}
    _gnr_remembered_as__ = None

    def __del__(self):
        try:
            self._gnr_members__.pop(id(self))
            if self._gnr_remembered_as__: self._gnr_namedmembers__.pop(self._gnr_remembered_as__)
        except:
            pass
        object.__del__(self)

    def rememberMe(self, name=None):
        """TODO

        :param name: TODO"""
        objid = id(self)
        #self._gnr_members__[objid]=weakref.ref(self)
        self._gnr_members__[objid] = self
        if name:
            old = self._gnr_namedmembers__.get(name, None)
            #if old: self._gnr_members__[old]()._gnr_remembered_as__=None
            if old: self._gnr_members__[old]._gnr_remembered_as__ = None
            self._gnr_remembered_as__ = name
            self._gnr_namedmembers__[name] = objid

    def rememberedMembers(cls):
        """TODO

        :param cls: TODO"""
        #return [v() for v in cls._gnr_members__.values()]
        return [v for v in list(cls._gnr_members__.values())]

    rememberedMembers = classmethod(rememberedMembers)

    def rememberedNamedMembers(cls):
        """TODO

        :param cls: TODO"""
        #return dict([(name,cls._gnr_members__[objid]()) for  name,objid in cls._gnr_namedmembers__.items()])
        return dict([(name, cls._gnr_members__[objid]) for  name, objid in list(cls._gnr_namedmembers__.items())])

    rememberedNamedMembers = classmethod(rememberedNamedMembers)

    def rememberedGet(cls, name):
        """TODO

        :param cls: TODO
        :param name: TODO"""
        objid = cls._gnr_namedmembers__.get(name, None)
        #if objid:return cls._gnr_members__[objid]()
        if objid: return cls._gnr_members__[objid]

    rememberedGet = classmethod(rememberedGet)


class GnrMetaString(object):
    """TODO"""
    _glossary = {}

    def glossary(cls):
        """TODO

        :param cls: TODO"""
        return list(cls._glossary.keys())

    glossary = classmethod(glossary)

    def __init__(self, value):
        self._glossary[value] = None
        self.value = value

    def __repr__(self):
        return '(*' + self.value + '*)'

    def __str__(self):
        return '(*)' + self.value + '*)'

    def __eq__(self, value):
        if isinstance(value, self.__class__):
            return bool(self.value == value.value)

class SuperdoTest(object):
    """TODO"""
    def __init__(self, first, second, alfa='alfadef', beta='betadef'):
        pass

class SuperdoTestChild(SuperdoTest, GnrAddOn):
    def __init__(self, a, b, alfa='alfachildef', beta='betachildefd', gamma=78, *args, **kwargs):
        if a == 'gino': a = 'pino'
        self.superdo()

class SuperdoTestChildX(SuperdoTest):
    def __init__(self, a, b, alfa='alfachildef', beta='betachildefd', gamma=78, *args, **kwargs):
        if a == 'gino': a = 'pino'
        GnrAddOn.dosuper(self)


class GnrExpandible(object):
    """TODO"""
    def __onmixin__(self, **kwargs):
        self.__expanders = []

    def addExpander(self, expander):
        """TODO

        :param expander: TODO
        """
        if not expander in self.__expanders:
            expander.parent = self
            #expander.parent=weakref.ref(self)
            self.__expanders.insert(0, expander)

    def delExpander(self, expander):
        """TODO

        :param expander: TODO
        """
        self.__expanders.remove(expander)

    def __getattr__(self, attr):
        for expander in self.__expanders:
            if hasattr(expander, attr):
                return getattr(expander, attr)
