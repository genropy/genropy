
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbagresolver import BagResolver

class BagNodeException(GnrException):
    pass

class BagNode(object):
    """BagNode is the element type which a Bag is composed of. That's why it's possible to say that a Bag
    is a collection of BagNodes. A BagNode is an object that gather within itself, three main things:
    
    * *label*: can be only a string.
    * *value*: can be anything even a BagNode. If you got the xml of the Bag it should be serializable
    * *attributes*: dictionary that contains node's metadata"""

    def __init__(self, parentbag, label, value=None, attr=None, resolver=None,
                 validators=None, _removeNullAttributes=True,_attributes=None):
        self.label = label
        self.locked = False
        self._value = None
        self.resolver = resolver
        self.parentbag = parentbag
        self._node_subscribers = {}
        self._validators = None
        if _attributes:
            self.attr = _attributes
            self._value = value
            return
        self.attr = {}
        if attr:
            self.setAttr(attr, trigger=False, _removeNullAttributes=_removeNullAttributes)
        if validators:
            self.setValidators(validators)
        self.setValue(value, trigger=False)
        
    def __eq__(self, other):
        """One BagNode is equal to another one if its key, value, attributes and resolvers are the same of the other one"""
        try:
            if isinstance(other, self.__class__) and (self.attr == other.attr):
                if self._resolver == None:
                    return self._value == other._value
                else:
                    return self._resolver == other._resolver
            else:
                return False
        except:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

            
    def setValidators(self, validators):
        """TODO"""
        for k, v in list(validators.items()):
            self.addValidator(k, v)
            
    def _get_parentbag(self):
        return self._parentbag
            #return self._parentbag()
            
    def _set_parentbag(self, parentbag):
        self._parentbag = None
        if parentbag != None:
            if parentbag.backref or True:
                #self._parentbag=weakref.ref(parentbag)
                self._parentbag = parentbag
                if hasattr(self._value,'_htraverse') and parentbag.backref:
                    self._value.setBackRef(node=self, parent=parentbag)

    parentbag = property(_get_parentbag, _set_parentbag)

    def _get_fullpath(self):
        if not self.parentbag is None:
            fullpath = self.parentbag.fullpath
            if not fullpath is None:
                return '%s.%s' % (fullpath, self.label)

    fullpath = property(_get_fullpath)

    def getLabel(self):
        """Return the node's label"""
        return self.label

    def setLabel(self, label):
        """Set node's label"""
        self.label = label

    @property
    def position(self):
        if self.parentbag is not None:
            #return self.parentbag.nodes.index(self)
            return [id(n) for n in self.parentbag.nodes].index(id(self))

    @property
    def tag(self):
        return self.attr.get('tag') or self.label

    def getValue(self, mode=''):
        """Return the value of the BagNode. It is called by the property .value
            
        :param mode='static': allow to get the resolver instance instead of the calculated value
        :param mode='weak': allow to get a weak ref stored in the node instead of the actual object"""
        if not self._resolver == None:
            if 'static' in mode:
                return self._value
            else:
                if self._resolver.readOnly:
                    return self._resolver() # value is not saved in bag, eventually is cached by resolver or lost
                if self._resolver.expired: # check to avoid triggers if value unchanged
                    self.value = self._resolver() # this may be a deferred
                return self._value
        return self._value
    
    def getFormattedValue(self,joiner=None,omitEmpty=True,mode='',**kwargs):
        from gnr.core.gnrbag import Bag
        v = self.getValue(mode=mode)

        if isinstance(v,Bag):
            v = v.getFormattedValue(joiner=joiner,omitEmpty=omitEmpty,mode=mode,**kwargs)
        else:
            v = self.attr.get('_formattedValue') or self.attr.get('_displayedValue') or v
        if v or not omitEmpty:
            return '%s: %s' %((self.attr.get('_valuelabel') or self.attr.get('name_long') or self.label.capitalize()),v)
        return ''

    def toJson(self,typed=True):
        from gnr.core.gnrbag import Bag
        value = self.value
        if isinstance(value,Bag):
            value = value.toJson(typed=typed,nested=True)
        return {"label":self.label,"value":value,"attr":self.attr}

    def setValue(self, value, trigger=True, _attributes=None, _updattr=None, _removeNullAttributes=True,_reason=None):
        """Set the node's value, unless the node is locked. This method is called by the property .value
        
        :param value: the value to set the new bag inherits the trigger of the parentBag and calls it sending an update event
        :param trigger: boolean. TODO
        """
        if self.locked:
            raise BagNodeException("Locked node %s" % self.label)
        if isinstance(value,BagResolver):
            self.resolver = value
            value = None
        elif isinstance(value, BagNode):
            _attributes = _attributes or {}
            _attributes.update(value.attr)
            value = value._value
        if hasattr(value, 'rootattributes'):
            rootattributes = value.rootattributes
            if rootattributes:
                _attributes = dict(_attributes or {})
                _attributes.update(rootattributes)
        oldvalue = self._value
        if self._validators:
            self._value = self._validators(value, oldvalue)
        else:
            self._value = value
        changed = oldvalue != self._value
        if not changed and _attributes:
            for attr_k,attr_v in list(_attributes.items()):
                if self.attr.get(attr_k) != attr_v:
                    changed = True
                    break
        trigger = trigger and  changed
        evt = 'upd_value'
        if _attributes != None:
            evt = 'upd_value_attr'
            self.setAttr(_attributes, trigger=False, _updattr=_updattr,
                         _removeNullAttributes=_removeNullAttributes)
        if trigger:
            for subscriber in list(self._node_subscribers.values()):
                subscriber(node=self, info=oldvalue, evt='upd_value')
        if self.parentbag != None and self.parentbag.backref:
            if hasattr(value,'_htraverse'):
                value.setBackRef(node=self, parent=self.parentbag)
            if trigger:
                self.parentbag._onNodeChanged(self, [self.label],
                                              oldvalue=oldvalue, evt=evt,reason=_reason)

    value = property(getValue, setValue)

    def getStaticValue(self):
        """Get node's value in static mode"""
        return self.getValue('static')
        
    def setStaticValue(self, value):
        """Set node's value in static mode"""
        self._value = value
        
    staticvalue = property(getStaticValue, setStaticValue)
        
    def _set_resolver(self, resolver):
        """Set a resolver in the node"""
        if not resolver is None:
            resolver.parentNode = self
        self._resolver = resolver
        
    def _get_resolver(self):
        """Get node's resolver
        """
        return self._resolver
        
    resolver = property(_get_resolver, _set_resolver)
        
    def resetResolver(self):
        """TODO"""
        self._resolver.reset()
        self.setValue(None)

    def diff(self,other):
        from gnr.core.gnrbag import Bag
        if self.label !=other.label:
            return 'Other label: %s' %other.label
        if self.attr != other.attr:
            return 'attributes self:%s --- other:%s' %(self.attr,other.attr) 
        if self._value != other._value:
            if isinstance(self._value,Bag):
                return 'value:%s' %self._value.diff(other._value)
            else:
                return 'value self:%s --- other:%s' %(self._value,other._value)

        
    def getAttr(self, label=None, default=None):
        """It returns the value of an attribute. You have to specify the attribute's label.
        If it doesn't exist then it returns a default value
        
        :param label: the attribute's label that should be get
        :param default: the default return value for a not found attribute"""
        if not label or label == '#':
            return self.attr
        return self.attr.get(label, default)
        
    def getInheritedAttributes(self):
        """TODO"""
        inherited = {}
        if self.parentbag:
            if self.parentbag.parentNode:
                inherited = self.parentbag.parentNode.getInheritedAttributes()
        inherited.update(self.attr)
        return inherited
        
    @property
    def parentNode(self):
        if self.parentbag:
            return self.parentbag.parentNode
    
    def attributeOwnerNode(self,attrname,**kwargs):
        curr = self
        if not 'attrvalue' in kwargs:
            while curr and not (attrname in curr.attr):
                curr = curr.parentNode
        else:
            attrvalue = kwargs['attrvalue']
            while curr and curr.attr.get(attrname)!=attrvalue:
                curr = curr.parentNode
        return curr
        
    def hasAttr(self, label=None, value=None):
        """Check if a node has the given pair label-value in its attributes' dictionary"""
        if not label in self.attr: return False
        if value: return (self.attr[label] == value)
        return True
        
    def setAttr(self, attr=None, trigger=True, _updattr=True, _removeNullAttributes=True, **kwargs):
        """It receives one or more key-value couple, passed as a dict or as named parameters,
        and sets them as attributes of the node.
            
        :param attr: the attribute that should be set into the node
        :param trigger: TODO
        """
        if not _updattr:
            self.attr.clear()
            #if self.locked:
            #raise BagNodeException("Locked node %s" % self.label)
        if self._node_subscribers and trigger:
            oldattr = dict(self.attr)
        if attr:
            self.attr.update(attr)
        if kwargs:
            self.attr.update(kwargs)
        if _removeNullAttributes:
            [self.attr.__delitem__(k) for k, v in list(self.attr.items()) if v == None]

        if trigger:
            if self._node_subscribers:
                upd_attrs = [k for k in list(self.attr.keys()) if (k not in list(oldattr.keys()) or self.attr[k] != oldattr[k])]
                for subscriber in list(self._node_subscribers.values()):
                    subscriber(node=self, info=upd_attrs, evt='upd_attrs')
            if self.parentbag != None and self.parentbag.backref:
                self.parentbag._onNodeChanged(self, [self.label], evt='upd_attrs',reason=trigger)

    def delAttr(self, *attrToDelete):
        """Receive one or more attributes' labels and remove them from the node's attributes"""
        if isinstance(attrToDelete, str):
            attrToDelete = attrToDelete.split(',')
        for attr in attrToDelete:
            if attr in list(self.attr.keys()):
                self.attr.pop(attr)

    def __str__(self):
        return 'BagNode : %s' % self.label

    def __repr__(self):
        return 'BagNode : %s at %i' % (self.label, id(self))

    def asTuple(self):
        """TODO"""
        return (self.label, self.value, self.attr, self.resolver)

    def addValidator(self, validator, parameterString):

        """Set a new validator into the BagValidationList of the node.
        If there are no validators into the node then addValidator instantiate
        a new BagValidationList and append the validator to it
        
        :param validator: the type of validation to set into the list of the node
        :param parameterString: the parameter for a single validation type"""
        from gnr.core.gnrbag import BagValidationList
        
        if self._validators is None:
            self._validators = BagValidationList(self)
        self._validators.add(validator, parameterString)

    def removeValidator(self, validator):
        """TODO"""
        if not self._validators is None:
            self._validators.remove(validator)

    def getValidatorData(self, validator, label=None, dflt=None):
        """TODO"""
        if not self._validators is None:
            return self._validators.getdata(validator, label=label, dflt=dflt)

    def subscribe(self, subscriberId, callback):
        """TODO
        
        :param subscriberId: TODO
        :param callback: TODO"""
        self._node_subscribers[subscriberId] = callback

    def unsubscribe(self, subscriberId):
        """TODO"""
        self._node_subscribers.pop(subscriberId)
