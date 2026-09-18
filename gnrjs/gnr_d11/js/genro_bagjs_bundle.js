var GenroBagJS = (() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/conventions.js
  var require_conventions = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/conventions.js"(exports) {
      "use strict";
      function find(list, predicate, ac) {
        if (ac === void 0) {
          ac = Array.prototype;
        }
        if (list && typeof ac.find === "function") {
          return ac.find.call(list, predicate);
        }
        for (var i = 0; i < list.length; i++) {
          if (Object.prototype.hasOwnProperty.call(list, i)) {
            var item = list[i];
            if (predicate.call(void 0, item, i, list)) {
              return item;
            }
          }
        }
      }
      function freeze(object, oc) {
        if (oc === void 0) {
          oc = Object;
        }
        return oc && typeof oc.freeze === "function" ? oc.freeze(object) : object;
      }
      function assign(target, source) {
        if (target === null || typeof target !== "object") {
          throw new TypeError("target is not an object");
        }
        for (var key in source) {
          if (Object.prototype.hasOwnProperty.call(source, key)) {
            target[key] = source[key];
          }
        }
        return target;
      }
      var MIME_TYPE = freeze({
        /**
         * `text/html`, the only mime type that triggers treating an XML document as HTML.
         *
         * @see DOMParser.SupportedType.isHTML
         * @see https://www.iana.org/assignments/media-types/text/html IANA MimeType registration
         * @see https://en.wikipedia.org/wiki/HTML Wikipedia
         * @see https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString MDN
         * @see https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-domparser-parsefromstring WHATWG HTML Spec
         */
        HTML: "text/html",
        /**
         * Helper method to check a mime type if it indicates an HTML document
         *
         * @param {string} [value]
         * @returns {boolean}
         *
         * @see https://www.iana.org/assignments/media-types/text/html IANA MimeType registration
         * @see https://en.wikipedia.org/wiki/HTML Wikipedia
         * @see https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString MDN
         * @see https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-domparser-parsefromstring 	 */
        isHTML: function(value) {
          return value === MIME_TYPE.HTML;
        },
        /**
         * `application/xml`, the standard mime type for XML documents.
         *
         * @see https://www.iana.org/assignments/media-types/application/xml IANA MimeType registration
         * @see https://tools.ietf.org/html/rfc7303#section-9.1 RFC 7303
         * @see https://en.wikipedia.org/wiki/XML_and_MIME Wikipedia
         */
        XML_APPLICATION: "application/xml",
        /**
         * `text/html`, an alias for `application/xml`.
         *
         * @see https://tools.ietf.org/html/rfc7303#section-9.2 RFC 7303
         * @see https://www.iana.org/assignments/media-types/text/xml IANA MimeType registration
         * @see https://en.wikipedia.org/wiki/XML_and_MIME Wikipedia
         */
        XML_TEXT: "text/xml",
        /**
         * `application/xhtml+xml`, indicates an XML document that has the default HTML namespace,
         * but is parsed as an XML document.
         *
         * @see https://www.iana.org/assignments/media-types/application/xhtml+xml IANA MimeType registration
         * @see https://dom.spec.whatwg.org/#dom-domimplementation-createdocument WHATWG DOM Spec
         * @see https://en.wikipedia.org/wiki/XHTML Wikipedia
         */
        XML_XHTML_APPLICATION: "application/xhtml+xml",
        /**
         * `image/svg+xml`,
         *
         * @see https://www.iana.org/assignments/media-types/image/svg+xml IANA MimeType registration
         * @see https://www.w3.org/TR/SVG11/ W3C SVG 1.1
         * @see https://en.wikipedia.org/wiki/Scalable_Vector_Graphics Wikipedia
         */
        XML_SVG_IMAGE: "image/svg+xml"
      });
      var NAMESPACE = freeze({
        /**
         * The XHTML namespace.
         *
         * @see http://www.w3.org/1999/xhtml
         */
        HTML: "http://www.w3.org/1999/xhtml",
        /**
         * Checks if `uri` equals `NAMESPACE.HTML`.
         *
         * @param {string} [uri]
         *
         * @see NAMESPACE.HTML
         */
        isHTML: function(uri) {
          return uri === NAMESPACE.HTML;
        },
        /**
         * The SVG namespace.
         *
         * @see http://www.w3.org/2000/svg
         */
        SVG: "http://www.w3.org/2000/svg",
        /**
         * The `xml:` namespace.
         *
         * @see http://www.w3.org/XML/1998/namespace
         */
        XML: "http://www.w3.org/XML/1998/namespace",
        /**
         * The `xmlns:` namespace
         *
         * @see https://www.w3.org/2000/xmlns/
         */
        XMLNS: "http://www.w3.org/2000/xmlns/"
      });
      exports.assign = assign;
      exports.find = find;
      exports.freeze = freeze;
      exports.MIME_TYPE = MIME_TYPE;
      exports.NAMESPACE = NAMESPACE;
    }
  });

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/dom.js
  var require_dom = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/dom.js"(exports) {
      var conventions = require_conventions();
      var find = conventions.find;
      var NAMESPACE = conventions.NAMESPACE;
      function notEmptyString(input) {
        return input !== "";
      }
      function splitOnASCIIWhitespace(input) {
        return input ? input.split(/[\t\n\f\r ]+/).filter(notEmptyString) : [];
      }
      function orderedSetReducer(current, element) {
        if (!current.hasOwnProperty(element)) {
          current[element] = true;
        }
        return current;
      }
      function toOrderedSet(input) {
        if (!input) return [];
        var list = splitOnASCIIWhitespace(input);
        return Object.keys(list.reduce(orderedSetReducer, {}));
      }
      function arrayIncludes(list) {
        return function(element) {
          return list && list.indexOf(element) !== -1;
        };
      }
      function copy(src, dest) {
        for (var p in src) {
          if (Object.prototype.hasOwnProperty.call(src, p)) {
            dest[p] = src[p];
          }
        }
      }
      function _extends(Class, Super) {
        var pt = Class.prototype;
        if (!(pt instanceof Super)) {
          let t2 = function() {
          };
          var t = t2;
          ;
          t2.prototype = Super.prototype;
          t2 = new t2();
          copy(pt, t2);
          Class.prototype = pt = t2;
        }
        if (pt.constructor != Class) {
          if (typeof Class != "function") {
            console.error("unknown Class:" + Class);
          }
          pt.constructor = Class;
        }
      }
      var NodeType = {};
      var ELEMENT_NODE = NodeType.ELEMENT_NODE = 1;
      var ATTRIBUTE_NODE = NodeType.ATTRIBUTE_NODE = 2;
      var TEXT_NODE = NodeType.TEXT_NODE = 3;
      var CDATA_SECTION_NODE = NodeType.CDATA_SECTION_NODE = 4;
      var ENTITY_REFERENCE_NODE = NodeType.ENTITY_REFERENCE_NODE = 5;
      var ENTITY_NODE = NodeType.ENTITY_NODE = 6;
      var PROCESSING_INSTRUCTION_NODE = NodeType.PROCESSING_INSTRUCTION_NODE = 7;
      var COMMENT_NODE = NodeType.COMMENT_NODE = 8;
      var DOCUMENT_NODE = NodeType.DOCUMENT_NODE = 9;
      var DOCUMENT_TYPE_NODE = NodeType.DOCUMENT_TYPE_NODE = 10;
      var DOCUMENT_FRAGMENT_NODE = NodeType.DOCUMENT_FRAGMENT_NODE = 11;
      var NOTATION_NODE = NodeType.NOTATION_NODE = 12;
      var ExceptionCode = {};
      var ExceptionMessage = {};
      var INDEX_SIZE_ERR = ExceptionCode.INDEX_SIZE_ERR = (ExceptionMessage[1] = "Index size error", 1);
      var DOMSTRING_SIZE_ERR = ExceptionCode.DOMSTRING_SIZE_ERR = (ExceptionMessage[2] = "DOMString size error", 2);
      var HIERARCHY_REQUEST_ERR = ExceptionCode.HIERARCHY_REQUEST_ERR = (ExceptionMessage[3] = "Hierarchy request error", 3);
      var WRONG_DOCUMENT_ERR = ExceptionCode.WRONG_DOCUMENT_ERR = (ExceptionMessage[4] = "Wrong document", 4);
      var INVALID_CHARACTER_ERR = ExceptionCode.INVALID_CHARACTER_ERR = (ExceptionMessage[5] = "Invalid character", 5);
      var NO_DATA_ALLOWED_ERR = ExceptionCode.NO_DATA_ALLOWED_ERR = (ExceptionMessage[6] = "No data allowed", 6);
      var NO_MODIFICATION_ALLOWED_ERR = ExceptionCode.NO_MODIFICATION_ALLOWED_ERR = (ExceptionMessage[7] = "No modification allowed", 7);
      var NOT_FOUND_ERR = ExceptionCode.NOT_FOUND_ERR = (ExceptionMessage[8] = "Not found", 8);
      var NOT_SUPPORTED_ERR = ExceptionCode.NOT_SUPPORTED_ERR = (ExceptionMessage[9] = "Not supported", 9);
      var INUSE_ATTRIBUTE_ERR = ExceptionCode.INUSE_ATTRIBUTE_ERR = (ExceptionMessage[10] = "Attribute in use", 10);
      var INVALID_STATE_ERR = ExceptionCode.INVALID_STATE_ERR = (ExceptionMessage[11] = "Invalid state", 11);
      var SYNTAX_ERR = ExceptionCode.SYNTAX_ERR = (ExceptionMessage[12] = "Syntax error", 12);
      var INVALID_MODIFICATION_ERR = ExceptionCode.INVALID_MODIFICATION_ERR = (ExceptionMessage[13] = "Invalid modification", 13);
      var NAMESPACE_ERR = ExceptionCode.NAMESPACE_ERR = (ExceptionMessage[14] = "Invalid namespace", 14);
      var INVALID_ACCESS_ERR = ExceptionCode.INVALID_ACCESS_ERR = (ExceptionMessage[15] = "Invalid access", 15);
      function DOMException(code, message) {
        if (message instanceof Error) {
          var error = message;
        } else {
          error = this;
          Error.call(this, ExceptionMessage[code]);
          this.message = ExceptionMessage[code];
          if (Error.captureStackTrace) Error.captureStackTrace(this, DOMException);
        }
        error.code = code;
        if (message) this.message = this.message + ": " + message;
        return error;
      }
      DOMException.prototype = Error.prototype;
      copy(ExceptionCode, DOMException);
      function NodeList() {
      }
      NodeList.prototype = {
        /**
         * The number of nodes in the list. The range of valid child node indices is 0 to length-1 inclusive.
         * @standard level1
         */
        length: 0,
        /**
         * Returns the indexth item in the collection. If index is greater than or equal to the number of nodes in the list, this returns null.
         * @standard level1
         * @param index  unsigned long
         *   Index into the collection.
         * @return Node
         * 	The node at the indexth position in the NodeList, or null if that is not a valid index.
         */
        item: function(index) {
          return index >= 0 && index < this.length ? this[index] : null;
        },
        toString: function(isHTML, nodeFilter) {
          for (var buf = [], i = 0; i < this.length; i++) {
            serializeToString(this[i], buf, isHTML, nodeFilter);
          }
          return buf.join("");
        },
        /**
         * @private
         * @param {function (Node):boolean} predicate
         * @returns {Node[]}
         */
        filter: function(predicate) {
          return Array.prototype.filter.call(this, predicate);
        },
        /**
         * @private
         * @param {Node} item
         * @returns {number}
         */
        indexOf: function(item) {
          return Array.prototype.indexOf.call(this, item);
        }
      };
      function LiveNodeList(node, refresh) {
        this._node = node;
        this._refresh = refresh;
        _updateLiveList(this);
      }
      function _updateLiveList(list) {
        var inc = list._node._inc || list._node.ownerDocument._inc;
        if (list._inc !== inc) {
          var ls = list._refresh(list._node);
          __set__(list, "length", ls.length);
          if (!list.$$length || ls.length < list.$$length) {
            for (var i = ls.length; i in list; i++) {
              if (Object.prototype.hasOwnProperty.call(list, i)) {
                delete list[i];
              }
            }
          }
          copy(ls, list);
          list._inc = inc;
        }
      }
      LiveNodeList.prototype.item = function(i) {
        _updateLiveList(this);
        return this[i] || null;
      };
      _extends(LiveNodeList, NodeList);
      function NamedNodeMap() {
      }
      function _findNodeIndex(list, node) {
        var i = list.length;
        while (i--) {
          if (list[i] === node) {
            return i;
          }
        }
      }
      function _addNamedNode(el, list, newAttr, oldAttr) {
        if (oldAttr) {
          list[_findNodeIndex(list, oldAttr)] = newAttr;
        } else {
          list[list.length++] = newAttr;
        }
        if (el) {
          newAttr.ownerElement = el;
          var doc = el.ownerDocument;
          if (doc) {
            oldAttr && _onRemoveAttribute(doc, el, oldAttr);
            _onAddAttribute(doc, el, newAttr);
          }
        }
      }
      function _removeNamedNode(el, list, attr) {
        var i = _findNodeIndex(list, attr);
        if (i >= 0) {
          var lastIndex = list.length - 1;
          while (i < lastIndex) {
            list[i] = list[++i];
          }
          list.length = lastIndex;
          if (el) {
            var doc = el.ownerDocument;
            if (doc) {
              _onRemoveAttribute(doc, el, attr);
              attr.ownerElement = null;
            }
          }
        } else {
          throw new DOMException(NOT_FOUND_ERR, new Error(el.tagName + "@" + attr));
        }
      }
      NamedNodeMap.prototype = {
        length: 0,
        item: NodeList.prototype.item,
        getNamedItem: function(key) {
          var i = this.length;
          while (i--) {
            var attr = this[i];
            if (attr.nodeName == key) {
              return attr;
            }
          }
        },
        setNamedItem: function(attr) {
          var el = attr.ownerElement;
          if (el && el != this._ownerElement) {
            throw new DOMException(INUSE_ATTRIBUTE_ERR);
          }
          var oldAttr = this.getNamedItem(attr.nodeName);
          _addNamedNode(this._ownerElement, this, attr, oldAttr);
          return oldAttr;
        },
        /* returns Node */
        setNamedItemNS: function(attr) {
          var el = attr.ownerElement, oldAttr;
          if (el && el != this._ownerElement) {
            throw new DOMException(INUSE_ATTRIBUTE_ERR);
          }
          oldAttr = this.getNamedItemNS(attr.namespaceURI, attr.localName);
          _addNamedNode(this._ownerElement, this, attr, oldAttr);
          return oldAttr;
        },
        /* returns Node */
        removeNamedItem: function(key) {
          var attr = this.getNamedItem(key);
          _removeNamedNode(this._ownerElement, this, attr);
          return attr;
        },
        // raises: NOT_FOUND_ERR,NO_MODIFICATION_ALLOWED_ERR
        //for level2
        removeNamedItemNS: function(namespaceURI, localName) {
          var attr = this.getNamedItemNS(namespaceURI, localName);
          _removeNamedNode(this._ownerElement, this, attr);
          return attr;
        },
        getNamedItemNS: function(namespaceURI, localName) {
          var i = this.length;
          while (i--) {
            var node = this[i];
            if (node.localName == localName && node.namespaceURI == namespaceURI) {
              return node;
            }
          }
          return null;
        }
      };
      function DOMImplementation() {
      }
      DOMImplementation.prototype = {
        /**
         * The DOMImplementation.hasFeature() method returns a Boolean flag indicating if a given feature is supported.
         * The different implementations fairly diverged in what kind of features were reported.
         * The latest version of the spec settled to force this method to always return true, where the functionality was accurate and in use.
         *
         * @deprecated It is deprecated and modern browsers return true in all cases.
         *
         * @param {string} feature
         * @param {string} [version]
         * @returns {boolean} always true
         *
         * @see https://developer.mozilla.org/en-US/docs/Web/API/DOMImplementation/hasFeature MDN
         * @see https://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-5CED94D7 DOM Level 1 Core
         * @see https://dom.spec.whatwg.org/#dom-domimplementation-hasfeature DOM Living Standard
         */
        hasFeature: function(feature, version2) {
          return true;
        },
        /**
         * Creates an XML Document object of the specified type with its document element.
         *
         * __It behaves slightly different from the description in the living standard__:
         * - There is no interface/class `XMLDocument`, it returns a `Document` instance.
         * - `contentType`, `encoding`, `mode`, `origin`, `url` fields are currently not declared.
         * - this implementation is not validating names or qualified names
         *   (when parsing XML strings, the SAX parser takes care of that)
         *
         * @param {string|null} namespaceURI
         * @param {string} qualifiedName
         * @param {DocumentType=null} doctype
         * @returns {Document}
         *
         * @see https://developer.mozilla.org/en-US/docs/Web/API/DOMImplementation/createDocument MDN
         * @see https://www.w3.org/TR/DOM-Level-2-Core/core.html#Level-2-Core-DOM-createDocument DOM Level 2 Core (initial)
         * @see https://dom.spec.whatwg.org/#dom-domimplementation-createdocument  DOM Level 2 Core
         *
         * @see https://dom.spec.whatwg.org/#validate-and-extract DOM: Validate and extract
         * @see https://www.w3.org/TR/xml/#NT-NameStartChar XML Spec: Names
         * @see https://www.w3.org/TR/xml-names/#ns-qualnames XML Namespaces: Qualified names
         */
        createDocument: function(namespaceURI, qualifiedName, doctype) {
          var doc = new Document();
          doc.implementation = this;
          doc.childNodes = new NodeList();
          doc.doctype = doctype || null;
          if (doctype) {
            doc.appendChild(doctype);
          }
          if (qualifiedName) {
            var root = doc.createElementNS(namespaceURI, qualifiedName);
            doc.appendChild(root);
          }
          return doc;
        },
        /**
         * Returns a doctype, with the given `qualifiedName`, `publicId`, and `systemId`.
         *
         * __This behavior is slightly different from the in the specs__:
         * - this implementation is not validating names or qualified names
         *   (when parsing XML strings, the SAX parser takes care of that)
         *
         * @param {string} qualifiedName
         * @param {string} [publicId]
         * @param {string} [systemId]
         * @returns {DocumentType} which can either be used with `DOMImplementation.createDocument` upon document creation
         * 				  or can be put into the document via methods like `Node.insertBefore()` or `Node.replaceChild()`
         *
         * @see https://developer.mozilla.org/en-US/docs/Web/API/DOMImplementation/createDocumentType MDN
         * @see https://www.w3.org/TR/DOM-Level-2-Core/core.html#Level-2-Core-DOM-createDocType DOM Level 2 Core
         * @see https://dom.spec.whatwg.org/#dom-domimplementation-createdocumenttype DOM Living Standard
         *
         * @see https://dom.spec.whatwg.org/#validate-and-extract DOM: Validate and extract
         * @see https://www.w3.org/TR/xml/#NT-NameStartChar XML Spec: Names
         * @see https://www.w3.org/TR/xml-names/#ns-qualnames XML Namespaces: Qualified names
         */
        createDocumentType: function(qualifiedName, publicId, systemId) {
          var node = new DocumentType();
          node.name = qualifiedName;
          node.nodeName = qualifiedName;
          node.publicId = publicId || "";
          node.systemId = systemId || "";
          return node;
        }
      };
      function Node() {
      }
      Node.prototype = {
        firstChild: null,
        lastChild: null,
        previousSibling: null,
        nextSibling: null,
        attributes: null,
        parentNode: null,
        childNodes: null,
        ownerDocument: null,
        nodeValue: null,
        namespaceURI: null,
        prefix: null,
        localName: null,
        // Modified in DOM Level 2:
        insertBefore: function(newChild, refChild) {
          return _insertBefore(this, newChild, refChild);
        },
        replaceChild: function(newChild, oldChild) {
          _insertBefore(this, newChild, oldChild, assertPreReplacementValidityInDocument);
          if (oldChild) {
            this.removeChild(oldChild);
          }
        },
        removeChild: function(oldChild) {
          return _removeChild(this, oldChild);
        },
        appendChild: function(newChild) {
          return this.insertBefore(newChild, null);
        },
        hasChildNodes: function() {
          return this.firstChild != null;
        },
        cloneNode: function(deep) {
          return cloneNode(this.ownerDocument || this, this, deep);
        },
        // Modified in DOM Level 2:
        normalize: function() {
          var child = this.firstChild;
          while (child) {
            var next = child.nextSibling;
            if (next && next.nodeType == TEXT_NODE && child.nodeType == TEXT_NODE) {
              this.removeChild(next);
              child.appendData(next.data);
            } else {
              child.normalize();
              child = next;
            }
          }
        },
        // Introduced in DOM Level 2:
        isSupported: function(feature, version2) {
          return this.ownerDocument.implementation.hasFeature(feature, version2);
        },
        // Introduced in DOM Level 2:
        hasAttributes: function() {
          return this.attributes.length > 0;
        },
        /**
         * Look up the prefix associated to the given namespace URI, starting from this node.
         * **The default namespace declarations are ignored by this method.**
         * See Namespace Prefix Lookup for details on the algorithm used by this method.
         *
         * _Note: The implementation seems to be incomplete when compared to the algorithm described in the specs._
         *
         * @param {string | null} namespaceURI
         * @returns {string | null}
         * @see https://www.w3.org/TR/DOM-Level-3-Core/core.html#Node3-lookupNamespacePrefix
         * @see https://www.w3.org/TR/DOM-Level-3-Core/namespaces-algorithms.html#lookupNamespacePrefixAlgo
         * @see https://dom.spec.whatwg.org/#dom-node-lookupprefix
         * @see https://github.com/xmldom/xmldom/issues/322
         */
        lookupPrefix: function(namespaceURI) {
          var el = this;
          while (el) {
            var map = el._nsMap;
            if (map) {
              for (var n in map) {
                if (Object.prototype.hasOwnProperty.call(map, n) && map[n] === namespaceURI) {
                  return n;
                }
              }
            }
            el = el.nodeType == ATTRIBUTE_NODE ? el.ownerDocument : el.parentNode;
          }
          return null;
        },
        // Introduced in DOM Level 3:
        lookupNamespaceURI: function(prefix) {
          var el = this;
          while (el) {
            var map = el._nsMap;
            if (map) {
              if (Object.prototype.hasOwnProperty.call(map, prefix)) {
                return map[prefix];
              }
            }
            el = el.nodeType == ATTRIBUTE_NODE ? el.ownerDocument : el.parentNode;
          }
          return null;
        },
        // Introduced in DOM Level 3:
        isDefaultNamespace: function(namespaceURI) {
          var prefix = this.lookupPrefix(namespaceURI);
          return prefix == null;
        }
      };
      function _xmlEncoder(c) {
        return c == "<" && "&lt;" || c == ">" && "&gt;" || c == "&" && "&amp;" || c == '"' && "&quot;" || "&#" + c.charCodeAt() + ";";
      }
      copy(NodeType, Node);
      copy(NodeType, Node.prototype);
      function _visitNode(node, callback) {
        if (callback(node)) {
          return true;
        }
        if (node = node.firstChild) {
          do {
            if (_visitNode(node, callback)) {
              return true;
            }
          } while (node = node.nextSibling);
        }
      }
      function Document() {
        this.ownerDocument = this;
      }
      function _onAddAttribute(doc, el, newAttr) {
        doc && doc._inc++;
        var ns = newAttr.namespaceURI;
        if (ns === NAMESPACE.XMLNS) {
          el._nsMap[newAttr.prefix ? newAttr.localName : ""] = newAttr.value;
        }
      }
      function _onRemoveAttribute(doc, el, newAttr, remove) {
        doc && doc._inc++;
        var ns = newAttr.namespaceURI;
        if (ns === NAMESPACE.XMLNS) {
          delete el._nsMap[newAttr.prefix ? newAttr.localName : ""];
        }
      }
      function _onUpdateChild(doc, el, newChild) {
        if (doc && doc._inc) {
          doc._inc++;
          var cs = el.childNodes;
          if (newChild) {
            cs[cs.length++] = newChild;
          } else {
            var child = el.firstChild;
            var i = 0;
            while (child) {
              cs[i++] = child;
              child = child.nextSibling;
            }
            cs.length = i;
            delete cs[cs.length];
          }
        }
      }
      function _removeChild(parentNode, child) {
        var previous = child.previousSibling;
        var next = child.nextSibling;
        if (previous) {
          previous.nextSibling = next;
        } else {
          parentNode.firstChild = next;
        }
        if (next) {
          next.previousSibling = previous;
        } else {
          parentNode.lastChild = previous;
        }
        child.parentNode = null;
        child.previousSibling = null;
        child.nextSibling = null;
        _onUpdateChild(parentNode.ownerDocument, parentNode);
        return child;
      }
      function hasValidParentNodeType(node) {
        return node && (node.nodeType === Node.DOCUMENT_NODE || node.nodeType === Node.DOCUMENT_FRAGMENT_NODE || node.nodeType === Node.ELEMENT_NODE);
      }
      function hasInsertableNodeType(node) {
        return node && (isElementNode(node) || isTextNode(node) || isDocTypeNode(node) || node.nodeType === Node.DOCUMENT_FRAGMENT_NODE || node.nodeType === Node.COMMENT_NODE || node.nodeType === Node.PROCESSING_INSTRUCTION_NODE);
      }
      function isDocTypeNode(node) {
        return node && node.nodeType === Node.DOCUMENT_TYPE_NODE;
      }
      function isElementNode(node) {
        return node && node.nodeType === Node.ELEMENT_NODE;
      }
      function isTextNode(node) {
        return node && node.nodeType === Node.TEXT_NODE;
      }
      function isElementInsertionPossible(doc, child) {
        var parentChildNodes = doc.childNodes || [];
        if (find(parentChildNodes, isElementNode) || isDocTypeNode(child)) {
          return false;
        }
        var docTypeNode = find(parentChildNodes, isDocTypeNode);
        return !(child && docTypeNode && parentChildNodes.indexOf(docTypeNode) > parentChildNodes.indexOf(child));
      }
      function isElementReplacementPossible(doc, child) {
        var parentChildNodes = doc.childNodes || [];
        function hasElementChildThatIsNotChild(node) {
          return isElementNode(node) && node !== child;
        }
        if (find(parentChildNodes, hasElementChildThatIsNotChild)) {
          return false;
        }
        var docTypeNode = find(parentChildNodes, isDocTypeNode);
        return !(child && docTypeNode && parentChildNodes.indexOf(docTypeNode) > parentChildNodes.indexOf(child));
      }
      function assertPreInsertionValidity1to5(parent, node, child) {
        if (!hasValidParentNodeType(parent)) {
          throw new DOMException(HIERARCHY_REQUEST_ERR, "Unexpected parent node type " + parent.nodeType);
        }
        if (child && child.parentNode !== parent) {
          throw new DOMException(NOT_FOUND_ERR, "child not in parent");
        }
        if (
          // 4. If `node` is not a DocumentFragment, DocumentType, Element, or CharacterData node, then throw a "HierarchyRequestError" DOMException.
          !hasInsertableNodeType(node) || // 5. If either `node` is a Text node and `parent` is a document,
          // the sax parser currently adds top level text nodes, this will be fixed in 0.9.0
          // || (node.nodeType === Node.TEXT_NODE && parent.nodeType === Node.DOCUMENT_NODE)
          // or `node` is a doctype and `parent` is not a document, then throw a "HierarchyRequestError" DOMException.
          isDocTypeNode(node) && parent.nodeType !== Node.DOCUMENT_NODE
        ) {
          throw new DOMException(
            HIERARCHY_REQUEST_ERR,
            "Unexpected node type " + node.nodeType + " for parent node type " + parent.nodeType
          );
        }
      }
      function assertPreInsertionValidityInDocument(parent, node, child) {
        var parentChildNodes = parent.childNodes || [];
        var nodeChildNodes = node.childNodes || [];
        if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
          var nodeChildElements = nodeChildNodes.filter(isElementNode);
          if (nodeChildElements.length > 1 || find(nodeChildNodes, isTextNode)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "More than one element or text in fragment");
          }
          if (nodeChildElements.length === 1 && !isElementInsertionPossible(parent, child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Element in fragment can not be inserted before doctype");
          }
        }
        if (isElementNode(node)) {
          if (!isElementInsertionPossible(parent, child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Only one element can be added and only after doctype");
          }
        }
        if (isDocTypeNode(node)) {
          if (find(parentChildNodes, isDocTypeNode)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Only one doctype is allowed");
          }
          var parentElementChild = find(parentChildNodes, isElementNode);
          if (child && parentChildNodes.indexOf(parentElementChild) < parentChildNodes.indexOf(child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Doctype can only be inserted before an element");
          }
          if (!child && parentElementChild) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Doctype can not be appended since element is present");
          }
        }
      }
      function assertPreReplacementValidityInDocument(parent, node, child) {
        var parentChildNodes = parent.childNodes || [];
        var nodeChildNodes = node.childNodes || [];
        if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
          var nodeChildElements = nodeChildNodes.filter(isElementNode);
          if (nodeChildElements.length > 1 || find(nodeChildNodes, isTextNode)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "More than one element or text in fragment");
          }
          if (nodeChildElements.length === 1 && !isElementReplacementPossible(parent, child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Element in fragment can not be inserted before doctype");
          }
        }
        if (isElementNode(node)) {
          if (!isElementReplacementPossible(parent, child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Only one element can be added and only after doctype");
          }
        }
        if (isDocTypeNode(node)) {
          let hasDoctypeChildThatIsNotChild2 = function(node2) {
            return isDocTypeNode(node2) && node2 !== child;
          };
          var hasDoctypeChildThatIsNotChild = hasDoctypeChildThatIsNotChild2;
          if (find(parentChildNodes, hasDoctypeChildThatIsNotChild2)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Only one doctype is allowed");
          }
          var parentElementChild = find(parentChildNodes, isElementNode);
          if (child && parentChildNodes.indexOf(parentElementChild) < parentChildNodes.indexOf(child)) {
            throw new DOMException(HIERARCHY_REQUEST_ERR, "Doctype can only be inserted before an element");
          }
        }
      }
      function _insertBefore(parent, node, child, _inDocumentAssertion) {
        assertPreInsertionValidity1to5(parent, node, child);
        if (parent.nodeType === Node.DOCUMENT_NODE) {
          (_inDocumentAssertion || assertPreInsertionValidityInDocument)(parent, node, child);
        }
        var cp = node.parentNode;
        if (cp) {
          cp.removeChild(node);
        }
        if (node.nodeType === DOCUMENT_FRAGMENT_NODE) {
          var newFirst = node.firstChild;
          if (newFirst == null) {
            return node;
          }
          var newLast = node.lastChild;
        } else {
          newFirst = newLast = node;
        }
        var pre = child ? child.previousSibling : parent.lastChild;
        newFirst.previousSibling = pre;
        newLast.nextSibling = child;
        if (pre) {
          pre.nextSibling = newFirst;
        } else {
          parent.firstChild = newFirst;
        }
        if (child == null) {
          parent.lastChild = newLast;
        } else {
          child.previousSibling = newLast;
        }
        do {
          newFirst.parentNode = parent;
          var targetDoc = parent.ownerDocument || parent;
          _updateOwnerDocument(newFirst, targetDoc);
        } while (newFirst !== newLast && (newFirst = newFirst.nextSibling));
        _onUpdateChild(parent.ownerDocument || parent, parent);
        if (node.nodeType == DOCUMENT_FRAGMENT_NODE) {
          node.firstChild = node.lastChild = null;
        }
        return node;
      }
      function _updateOwnerDocument(node, newOwnerDocument) {
        if (node.ownerDocument === newOwnerDocument) {
          return;
        }
        node.ownerDocument = newOwnerDocument;
        if (node.nodeType === ELEMENT_NODE && node.attributes) {
          for (var i = 0; i < node.attributes.length; i++) {
            var attr = node.attributes.item(i);
            if (attr) {
              attr.ownerDocument = newOwnerDocument;
            }
          }
        }
        var child = node.firstChild;
        while (child) {
          _updateOwnerDocument(child, newOwnerDocument);
          child = child.nextSibling;
        }
      }
      function _appendSingleChild(parentNode, newChild) {
        if (newChild.parentNode) {
          newChild.parentNode.removeChild(newChild);
        }
        newChild.parentNode = parentNode;
        newChild.previousSibling = parentNode.lastChild;
        newChild.nextSibling = null;
        if (newChild.previousSibling) {
          newChild.previousSibling.nextSibling = newChild;
        } else {
          parentNode.firstChild = newChild;
        }
        parentNode.lastChild = newChild;
        _onUpdateChild(parentNode.ownerDocument, parentNode, newChild);
        var targetDoc = parentNode.ownerDocument || parentNode;
        _updateOwnerDocument(newChild, targetDoc);
        return newChild;
      }
      Document.prototype = {
        //implementation : null,
        nodeName: "#document",
        nodeType: DOCUMENT_NODE,
        /**
         * The DocumentType node of the document.
         *
         * @readonly
         * @type DocumentType
         */
        doctype: null,
        documentElement: null,
        _inc: 1,
        insertBefore: function(newChild, refChild) {
          if (newChild.nodeType == DOCUMENT_FRAGMENT_NODE) {
            var child = newChild.firstChild;
            while (child) {
              var next = child.nextSibling;
              this.insertBefore(child, refChild);
              child = next;
            }
            return newChild;
          }
          _insertBefore(this, newChild, refChild);
          _updateOwnerDocument(newChild, this);
          if (this.documentElement === null && newChild.nodeType === ELEMENT_NODE) {
            this.documentElement = newChild;
          }
          return newChild;
        },
        removeChild: function(oldChild) {
          if (this.documentElement == oldChild) {
            this.documentElement = null;
          }
          return _removeChild(this, oldChild);
        },
        replaceChild: function(newChild, oldChild) {
          _insertBefore(this, newChild, oldChild, assertPreReplacementValidityInDocument);
          _updateOwnerDocument(newChild, this);
          if (oldChild) {
            this.removeChild(oldChild);
          }
          if (isElementNode(newChild)) {
            this.documentElement = newChild;
          }
        },
        // Introduced in DOM Level 2:
        importNode: function(importedNode, deep) {
          return importNode(this, importedNode, deep);
        },
        // Introduced in DOM Level 2:
        getElementById: function(id) {
          var rtv = null;
          _visitNode(this.documentElement, function(node) {
            if (node.nodeType == ELEMENT_NODE) {
              if (node.getAttribute("id") == id) {
                rtv = node;
                return true;
              }
            }
          });
          return rtv;
        },
        /**
         * The `getElementsByClassName` method of `Document` interface returns an array-like object
         * of all child elements which have **all** of the given class name(s).
         *
         * Returns an empty list if `classeNames` is an empty string or only contains HTML white space characters.
         *
         *
         * Warning: This is a live LiveNodeList.
         * Changes in the DOM will reflect in the array as the changes occur.
         * If an element selected by this array no longer qualifies for the selector,
         * it will automatically be removed. Be aware of this for iteration purposes.
         *
         * @param {string} classNames is a string representing the class name(s) to match; multiple class names are separated by (ASCII-)whitespace
         *
         * @see https://developer.mozilla.org/en-US/docs/Web/API/Document/getElementsByClassName
         * @see https://dom.spec.whatwg.org/#concept-getelementsbyclassname
         */
        getElementsByClassName: function(classNames) {
          var classNamesSet = toOrderedSet(classNames);
          return new LiveNodeList(this, function(base) {
            var ls = [];
            if (classNamesSet.length > 0) {
              _visitNode(base.documentElement, function(node) {
                if (node !== base && node.nodeType === ELEMENT_NODE) {
                  var nodeClassNames = node.getAttribute("class");
                  if (nodeClassNames) {
                    var matches = classNames === nodeClassNames;
                    if (!matches) {
                      var nodeClassNamesSet = toOrderedSet(nodeClassNames);
                      matches = classNamesSet.every(arrayIncludes(nodeClassNamesSet));
                    }
                    if (matches) {
                      ls.push(node);
                    }
                  }
                }
              });
            }
            return ls;
          });
        },
        //document factory method:
        createElement: function(tagName) {
          var node = new Element();
          node.ownerDocument = this;
          node.nodeName = tagName;
          node.tagName = tagName;
          node.localName = tagName;
          node.childNodes = new NodeList();
          var attrs = node.attributes = new NamedNodeMap();
          attrs._ownerElement = node;
          return node;
        },
        createDocumentFragment: function() {
          var node = new DocumentFragment();
          node.ownerDocument = this;
          node.childNodes = new NodeList();
          return node;
        },
        createTextNode: function(data) {
          var node = new Text();
          node.ownerDocument = this;
          node.appendData(data);
          return node;
        },
        createComment: function(data) {
          var node = new Comment();
          node.ownerDocument = this;
          node.appendData(data);
          return node;
        },
        createCDATASection: function(data) {
          var node = new CDATASection();
          node.ownerDocument = this;
          node.appendData(data);
          return node;
        },
        createProcessingInstruction: function(target, data) {
          var node = new ProcessingInstruction();
          node.ownerDocument = this;
          node.tagName = node.nodeName = node.target = target;
          node.nodeValue = node.data = data;
          return node;
        },
        createAttribute: function(name) {
          var node = new Attr();
          node.ownerDocument = this;
          node.name = name;
          node.nodeName = name;
          node.localName = name;
          node.specified = true;
          return node;
        },
        createEntityReference: function(name) {
          var node = new EntityReference();
          node.ownerDocument = this;
          node.nodeName = name;
          return node;
        },
        // Introduced in DOM Level 2:
        createElementNS: function(namespaceURI, qualifiedName) {
          var node = new Element();
          var pl = qualifiedName.split(":");
          var attrs = node.attributes = new NamedNodeMap();
          node.childNodes = new NodeList();
          node.ownerDocument = this;
          node.nodeName = qualifiedName;
          node.tagName = qualifiedName;
          node.namespaceURI = namespaceURI;
          if (pl.length == 2) {
            node.prefix = pl[0];
            node.localName = pl[1];
          } else {
            node.localName = qualifiedName;
          }
          attrs._ownerElement = node;
          return node;
        },
        // Introduced in DOM Level 2:
        createAttributeNS: function(namespaceURI, qualifiedName) {
          var node = new Attr();
          var pl = qualifiedName.split(":");
          node.ownerDocument = this;
          node.nodeName = qualifiedName;
          node.name = qualifiedName;
          node.namespaceURI = namespaceURI;
          node.specified = true;
          if (pl.length == 2) {
            node.prefix = pl[0];
            node.localName = pl[1];
          } else {
            node.localName = qualifiedName;
          }
          return node;
        }
      };
      _extends(Document, Node);
      function Element() {
        this._nsMap = {};
      }
      Element.prototype = {
        nodeType: ELEMENT_NODE,
        hasAttribute: function(name) {
          return this.getAttributeNode(name) != null;
        },
        getAttribute: function(name) {
          var attr = this.getAttributeNode(name);
          return attr && attr.value || "";
        },
        getAttributeNode: function(name) {
          return this.attributes.getNamedItem(name);
        },
        setAttribute: function(name, value) {
          var attr = this.ownerDocument.createAttribute(name);
          attr.value = attr.nodeValue = "" + value;
          this.setAttributeNode(attr);
        },
        removeAttribute: function(name) {
          var attr = this.getAttributeNode(name);
          attr && this.removeAttributeNode(attr);
        },
        //four real opeartion method
        appendChild: function(newChild) {
          if (newChild.nodeType === DOCUMENT_FRAGMENT_NODE) {
            return this.insertBefore(newChild, null);
          } else {
            return _appendSingleChild(this, newChild);
          }
        },
        setAttributeNode: function(newAttr) {
          return this.attributes.setNamedItem(newAttr);
        },
        setAttributeNodeNS: function(newAttr) {
          return this.attributes.setNamedItemNS(newAttr);
        },
        removeAttributeNode: function(oldAttr) {
          return this.attributes.removeNamedItem(oldAttr.nodeName);
        },
        //get real attribute name,and remove it by removeAttributeNode
        removeAttributeNS: function(namespaceURI, localName) {
          var old = this.getAttributeNodeNS(namespaceURI, localName);
          old && this.removeAttributeNode(old);
        },
        hasAttributeNS: function(namespaceURI, localName) {
          return this.getAttributeNodeNS(namespaceURI, localName) != null;
        },
        getAttributeNS: function(namespaceURI, localName) {
          var attr = this.getAttributeNodeNS(namespaceURI, localName);
          return attr && attr.value || "";
        },
        setAttributeNS: function(namespaceURI, qualifiedName, value) {
          var attr = this.ownerDocument.createAttributeNS(namespaceURI, qualifiedName);
          attr.value = attr.nodeValue = "" + value;
          this.setAttributeNode(attr);
        },
        getAttributeNodeNS: function(namespaceURI, localName) {
          return this.attributes.getNamedItemNS(namespaceURI, localName);
        },
        getElementsByTagName: function(tagName) {
          return new LiveNodeList(this, function(base) {
            var ls = [];
            _visitNode(base, function(node) {
              if (node !== base && node.nodeType == ELEMENT_NODE && (tagName === "*" || node.tagName == tagName)) {
                ls.push(node);
              }
            });
            return ls;
          });
        },
        getElementsByTagNameNS: function(namespaceURI, localName) {
          return new LiveNodeList(this, function(base) {
            var ls = [];
            _visitNode(base, function(node) {
              if (node !== base && node.nodeType === ELEMENT_NODE && (namespaceURI === "*" || node.namespaceURI === namespaceURI) && (localName === "*" || node.localName == localName)) {
                ls.push(node);
              }
            });
            return ls;
          });
        }
      };
      Document.prototype.getElementsByTagName = Element.prototype.getElementsByTagName;
      Document.prototype.getElementsByTagNameNS = Element.prototype.getElementsByTagNameNS;
      _extends(Element, Node);
      function Attr() {
      }
      Attr.prototype.nodeType = ATTRIBUTE_NODE;
      _extends(Attr, Node);
      function CharacterData() {
      }
      CharacterData.prototype = {
        data: "",
        substringData: function(offset, count) {
          return this.data.substring(offset, offset + count);
        },
        appendData: function(text) {
          text = this.data + text;
          this.nodeValue = this.data = text;
          this.length = text.length;
        },
        insertData: function(offset, text) {
          this.replaceData(offset, 0, text);
        },
        appendChild: function(newChild) {
          throw new Error(ExceptionMessage[HIERARCHY_REQUEST_ERR]);
        },
        deleteData: function(offset, count) {
          this.replaceData(offset, count, "");
        },
        replaceData: function(offset, count, text) {
          var start = this.data.substring(0, offset);
          var end = this.data.substring(offset + count);
          text = start + text + end;
          this.nodeValue = this.data = text;
          this.length = text.length;
        }
      };
      _extends(CharacterData, Node);
      function Text() {
      }
      Text.prototype = {
        nodeName: "#text",
        nodeType: TEXT_NODE,
        splitText: function(offset) {
          var text = this.data;
          var newText = text.substring(offset);
          text = text.substring(0, offset);
          this.data = this.nodeValue = text;
          this.length = text.length;
          var newNode = this.ownerDocument.createTextNode(newText);
          if (this.parentNode) {
            this.parentNode.insertBefore(newNode, this.nextSibling);
          }
          return newNode;
        }
      };
      _extends(Text, CharacterData);
      function Comment() {
      }
      Comment.prototype = {
        nodeName: "#comment",
        nodeType: COMMENT_NODE
      };
      _extends(Comment, CharacterData);
      function CDATASection() {
      }
      CDATASection.prototype = {
        nodeName: "#cdata-section",
        nodeType: CDATA_SECTION_NODE
      };
      _extends(CDATASection, CharacterData);
      function DocumentType() {
      }
      DocumentType.prototype.nodeType = DOCUMENT_TYPE_NODE;
      _extends(DocumentType, Node);
      function Notation() {
      }
      Notation.prototype.nodeType = NOTATION_NODE;
      _extends(Notation, Node);
      function Entity() {
      }
      Entity.prototype.nodeType = ENTITY_NODE;
      _extends(Entity, Node);
      function EntityReference() {
      }
      EntityReference.prototype.nodeType = ENTITY_REFERENCE_NODE;
      _extends(EntityReference, Node);
      function DocumentFragment() {
      }
      DocumentFragment.prototype.nodeName = "#document-fragment";
      DocumentFragment.prototype.nodeType = DOCUMENT_FRAGMENT_NODE;
      _extends(DocumentFragment, Node);
      function ProcessingInstruction() {
      }
      ProcessingInstruction.prototype.nodeType = PROCESSING_INSTRUCTION_NODE;
      _extends(ProcessingInstruction, Node);
      function XMLSerializer2() {
      }
      XMLSerializer2.prototype.serializeToString = function(node, isHtml, nodeFilter) {
        return nodeSerializeToString.call(node, isHtml, nodeFilter);
      };
      Node.prototype.toString = nodeSerializeToString;
      function nodeSerializeToString(isHtml, nodeFilter) {
        var buf = [];
        var refNode = this.nodeType == 9 && this.documentElement || this;
        var prefix = refNode.prefix;
        var uri = refNode.namespaceURI;
        if (uri && prefix == null) {
          var prefix = refNode.lookupPrefix(uri);
          if (prefix == null) {
            var visibleNamespaces = [
              { namespace: uri, prefix: null }
              //{namespace:uri,prefix:''}
            ];
          }
        }
        serializeToString(this, buf, isHtml, nodeFilter, visibleNamespaces);
        return buf.join("");
      }
      function needNamespaceDefine(node, isHTML, visibleNamespaces) {
        var prefix = node.prefix || "";
        var uri = node.namespaceURI;
        if (!uri) {
          return false;
        }
        if (prefix === "xml" && uri === NAMESPACE.XML || uri === NAMESPACE.XMLNS) {
          return false;
        }
        var i = visibleNamespaces.length;
        while (i--) {
          var ns = visibleNamespaces[i];
          if (ns.prefix === prefix) {
            return ns.namespace !== uri;
          }
        }
        return true;
      }
      function addSerializedAttribute(buf, qualifiedName, value) {
        buf.push(" ", qualifiedName, '="', value.replace(/[<>&"\t\n\r]/g, _xmlEncoder), '"');
      }
      function serializeToString(node, buf, isHTML, nodeFilter, visibleNamespaces) {
        if (!visibleNamespaces) {
          visibleNamespaces = [];
        }
        if (nodeFilter) {
          node = nodeFilter(node);
          if (node) {
            if (typeof node == "string") {
              buf.push(node);
              return;
            }
          } else {
            return;
          }
        }
        switch (node.nodeType) {
          case ELEMENT_NODE:
            var attrs = node.attributes;
            var len = attrs.length;
            var child = node.firstChild;
            var nodeName = node.tagName;
            isHTML = NAMESPACE.isHTML(node.namespaceURI) || isHTML;
            var prefixedNodeName = nodeName;
            if (!isHTML && !node.prefix && node.namespaceURI) {
              var defaultNS;
              for (var ai = 0; ai < attrs.length; ai++) {
                if (attrs.item(ai).name === "xmlns") {
                  defaultNS = attrs.item(ai).value;
                  break;
                }
              }
              if (!defaultNS) {
                for (var nsi = visibleNamespaces.length - 1; nsi >= 0; nsi--) {
                  var namespace = visibleNamespaces[nsi];
                  if (namespace.prefix === "" && namespace.namespace === node.namespaceURI) {
                    defaultNS = namespace.namespace;
                    break;
                  }
                }
              }
              if (defaultNS !== node.namespaceURI) {
                for (var nsi = visibleNamespaces.length - 1; nsi >= 0; nsi--) {
                  var namespace = visibleNamespaces[nsi];
                  if (namespace.namespace === node.namespaceURI) {
                    if (namespace.prefix) {
                      prefixedNodeName = namespace.prefix + ":" + nodeName;
                    }
                    break;
                  }
                }
              }
            }
            buf.push("<", prefixedNodeName);
            for (var i = 0; i < len; i++) {
              var attr = attrs.item(i);
              if (attr.prefix == "xmlns") {
                visibleNamespaces.push({ prefix: attr.localName, namespace: attr.value });
              } else if (attr.nodeName == "xmlns") {
                visibleNamespaces.push({ prefix: "", namespace: attr.value });
              }
            }
            for (var i = 0; i < len; i++) {
              var attr = attrs.item(i);
              if (needNamespaceDefine(attr, isHTML, visibleNamespaces)) {
                var prefix = attr.prefix || "";
                var uri = attr.namespaceURI;
                addSerializedAttribute(buf, prefix ? "xmlns:" + prefix : "xmlns", uri);
                visibleNamespaces.push({ prefix, namespace: uri });
              }
              serializeToString(attr, buf, isHTML, nodeFilter, visibleNamespaces);
            }
            if (nodeName === prefixedNodeName && needNamespaceDefine(node, isHTML, visibleNamespaces)) {
              var prefix = node.prefix || "";
              var uri = node.namespaceURI;
              addSerializedAttribute(buf, prefix ? "xmlns:" + prefix : "xmlns", uri);
              visibleNamespaces.push({ prefix, namespace: uri });
            }
            if (child || isHTML && !/^(?:meta|link|img|br|hr|input)$/i.test(nodeName)) {
              buf.push(">");
              if (isHTML && /^script$/i.test(nodeName)) {
                while (child) {
                  if (child.data) {
                    buf.push(child.data);
                  } else {
                    serializeToString(child, buf, isHTML, nodeFilter, visibleNamespaces.slice());
                  }
                  child = child.nextSibling;
                }
              } else {
                while (child) {
                  serializeToString(child, buf, isHTML, nodeFilter, visibleNamespaces.slice());
                  child = child.nextSibling;
                }
              }
              buf.push("</", prefixedNodeName, ">");
            } else {
              buf.push("/>");
            }
            return;
          case DOCUMENT_NODE:
          case DOCUMENT_FRAGMENT_NODE:
            var child = node.firstChild;
            while (child) {
              serializeToString(child, buf, isHTML, nodeFilter, visibleNamespaces.slice());
              child = child.nextSibling;
            }
            return;
          case ATTRIBUTE_NODE:
            return addSerializedAttribute(buf, node.name, node.value);
          case TEXT_NODE:
            return buf.push(
              node.data.replace(/[<&>]/g, _xmlEncoder)
            );
          case CDATA_SECTION_NODE:
            return buf.push("<![CDATA[", node.data, "]]>");
          case COMMENT_NODE:
            return buf.push("<!--", node.data, "-->");
          case DOCUMENT_TYPE_NODE:
            var pubid = node.publicId;
            var sysid = node.systemId;
            buf.push("<!DOCTYPE ", node.name);
            if (pubid) {
              buf.push(" PUBLIC ", pubid);
              if (sysid && sysid != ".") {
                buf.push(" ", sysid);
              }
              buf.push(">");
            } else if (sysid && sysid != ".") {
              buf.push(" SYSTEM ", sysid, ">");
            } else {
              var sub = node.internalSubset;
              if (sub) {
                buf.push(" [", sub, "]");
              }
              buf.push(">");
            }
            return;
          case PROCESSING_INSTRUCTION_NODE:
            return buf.push("<?", node.target, " ", node.data, "?>");
          case ENTITY_REFERENCE_NODE:
            return buf.push("&", node.nodeName, ";");
          //case ENTITY_NODE:
          //case NOTATION_NODE:
          default:
            buf.push("??", node.nodeName);
        }
      }
      function importNode(doc, node, deep) {
        var node2;
        switch (node.nodeType) {
          case ELEMENT_NODE:
            node2 = node.cloneNode(false);
            node2.ownerDocument = doc;
          //var attrs = node2.attributes;
          //var len = attrs.length;
          //for(var i=0;i<len;i++){
          //node2.setAttributeNodeNS(importNode(doc,attrs.item(i),deep));
          //}
          case DOCUMENT_FRAGMENT_NODE:
            break;
          case ATTRIBUTE_NODE:
            deep = true;
            break;
        }
        if (!node2) {
          node2 = node.cloneNode(false);
        }
        node2.ownerDocument = doc;
        node2.parentNode = null;
        if (deep) {
          var child = node.firstChild;
          while (child) {
            node2.appendChild(importNode(doc, child, deep));
            child = child.nextSibling;
          }
        }
        return node2;
      }
      function cloneNode(doc, node, deep) {
        var node2 = new node.constructor();
        for (var n in node) {
          if (Object.prototype.hasOwnProperty.call(node, n)) {
            var v = node[n];
            if (typeof v != "object") {
              if (v != node2[n]) {
                node2[n] = v;
              }
            }
          }
        }
        if (node.childNodes) {
          node2.childNodes = new NodeList();
        }
        node2.ownerDocument = doc;
        switch (node2.nodeType) {
          case ELEMENT_NODE:
            var attrs = node.attributes;
            var attrs2 = node2.attributes = new NamedNodeMap();
            var len = attrs.length;
            attrs2._ownerElement = node2;
            for (var i = 0; i < len; i++) {
              node2.setAttributeNode(cloneNode(doc, attrs.item(i), true));
            }
            break;
            ;
          case ATTRIBUTE_NODE:
            deep = true;
        }
        if (deep) {
          var child = node.firstChild;
          while (child) {
            node2.appendChild(cloneNode(doc, child, deep));
            child = child.nextSibling;
          }
        }
        return node2;
      }
      function __set__(object, key, value) {
        object[key] = value;
      }
      try {
        if (Object.defineProperty) {
          let getTextContent2 = function(node) {
            switch (node.nodeType) {
              case ELEMENT_NODE:
              case DOCUMENT_FRAGMENT_NODE:
                var buf = [];
                node = node.firstChild;
                while (node) {
                  if (node.nodeType !== 7 && node.nodeType !== 8) {
                    buf.push(getTextContent2(node));
                  }
                  node = node.nextSibling;
                }
                return buf.join("");
              default:
                return node.nodeValue;
            }
          };
          getTextContent = getTextContent2;
          Object.defineProperty(LiveNodeList.prototype, "length", {
            get: function() {
              _updateLiveList(this);
              return this.$$length;
            }
          });
          Object.defineProperty(Node.prototype, "textContent", {
            get: function() {
              return getTextContent2(this);
            },
            set: function(data) {
              switch (this.nodeType) {
                case ELEMENT_NODE:
                case DOCUMENT_FRAGMENT_NODE:
                  while (this.firstChild) {
                    this.removeChild(this.firstChild);
                  }
                  if (data || String(data)) {
                    this.appendChild(this.ownerDocument.createTextNode(data));
                  }
                  break;
                default:
                  this.data = data;
                  this.value = data;
                  this.nodeValue = data;
              }
            }
          });
          __set__ = function(object, key, value) {
            object["$$" + key] = value;
          };
        }
      } catch (e) {
      }
      var getTextContent;
      exports.DocumentType = DocumentType;
      exports.DOMException = DOMException;
      exports.DOMImplementation = DOMImplementation;
      exports.Element = Element;
      exports.Node = Node;
      exports.NodeList = NodeList;
      exports.XMLSerializer = XMLSerializer2;
    }
  });

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/entities.js
  var require_entities = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/entities.js"(exports) {
      "use strict";
      var freeze = require_conventions().freeze;
      exports.XML_ENTITIES = freeze({
        amp: "&",
        apos: "'",
        gt: ">",
        lt: "<",
        quot: '"'
      });
      exports.HTML_ENTITIES = freeze({
        Aacute: "\xC1",
        aacute: "\xE1",
        Abreve: "\u0102",
        abreve: "\u0103",
        ac: "\u223E",
        acd: "\u223F",
        acE: "\u223E\u0333",
        Acirc: "\xC2",
        acirc: "\xE2",
        acute: "\xB4",
        Acy: "\u0410",
        acy: "\u0430",
        AElig: "\xC6",
        aelig: "\xE6",
        af: "\u2061",
        Afr: "\u{1D504}",
        afr: "\u{1D51E}",
        Agrave: "\xC0",
        agrave: "\xE0",
        alefsym: "\u2135",
        aleph: "\u2135",
        Alpha: "\u0391",
        alpha: "\u03B1",
        Amacr: "\u0100",
        amacr: "\u0101",
        amalg: "\u2A3F",
        AMP: "&",
        amp: "&",
        And: "\u2A53",
        and: "\u2227",
        andand: "\u2A55",
        andd: "\u2A5C",
        andslope: "\u2A58",
        andv: "\u2A5A",
        ang: "\u2220",
        ange: "\u29A4",
        angle: "\u2220",
        angmsd: "\u2221",
        angmsdaa: "\u29A8",
        angmsdab: "\u29A9",
        angmsdac: "\u29AA",
        angmsdad: "\u29AB",
        angmsdae: "\u29AC",
        angmsdaf: "\u29AD",
        angmsdag: "\u29AE",
        angmsdah: "\u29AF",
        angrt: "\u221F",
        angrtvb: "\u22BE",
        angrtvbd: "\u299D",
        angsph: "\u2222",
        angst: "\xC5",
        angzarr: "\u237C",
        Aogon: "\u0104",
        aogon: "\u0105",
        Aopf: "\u{1D538}",
        aopf: "\u{1D552}",
        ap: "\u2248",
        apacir: "\u2A6F",
        apE: "\u2A70",
        ape: "\u224A",
        apid: "\u224B",
        apos: "'",
        ApplyFunction: "\u2061",
        approx: "\u2248",
        approxeq: "\u224A",
        Aring: "\xC5",
        aring: "\xE5",
        Ascr: "\u{1D49C}",
        ascr: "\u{1D4B6}",
        Assign: "\u2254",
        ast: "*",
        asymp: "\u2248",
        asympeq: "\u224D",
        Atilde: "\xC3",
        atilde: "\xE3",
        Auml: "\xC4",
        auml: "\xE4",
        awconint: "\u2233",
        awint: "\u2A11",
        backcong: "\u224C",
        backepsilon: "\u03F6",
        backprime: "\u2035",
        backsim: "\u223D",
        backsimeq: "\u22CD",
        Backslash: "\u2216",
        Barv: "\u2AE7",
        barvee: "\u22BD",
        Barwed: "\u2306",
        barwed: "\u2305",
        barwedge: "\u2305",
        bbrk: "\u23B5",
        bbrktbrk: "\u23B6",
        bcong: "\u224C",
        Bcy: "\u0411",
        bcy: "\u0431",
        bdquo: "\u201E",
        becaus: "\u2235",
        Because: "\u2235",
        because: "\u2235",
        bemptyv: "\u29B0",
        bepsi: "\u03F6",
        bernou: "\u212C",
        Bernoullis: "\u212C",
        Beta: "\u0392",
        beta: "\u03B2",
        beth: "\u2136",
        between: "\u226C",
        Bfr: "\u{1D505}",
        bfr: "\u{1D51F}",
        bigcap: "\u22C2",
        bigcirc: "\u25EF",
        bigcup: "\u22C3",
        bigodot: "\u2A00",
        bigoplus: "\u2A01",
        bigotimes: "\u2A02",
        bigsqcup: "\u2A06",
        bigstar: "\u2605",
        bigtriangledown: "\u25BD",
        bigtriangleup: "\u25B3",
        biguplus: "\u2A04",
        bigvee: "\u22C1",
        bigwedge: "\u22C0",
        bkarow: "\u290D",
        blacklozenge: "\u29EB",
        blacksquare: "\u25AA",
        blacktriangle: "\u25B4",
        blacktriangledown: "\u25BE",
        blacktriangleleft: "\u25C2",
        blacktriangleright: "\u25B8",
        blank: "\u2423",
        blk12: "\u2592",
        blk14: "\u2591",
        blk34: "\u2593",
        block: "\u2588",
        bne: "=\u20E5",
        bnequiv: "\u2261\u20E5",
        bNot: "\u2AED",
        bnot: "\u2310",
        Bopf: "\u{1D539}",
        bopf: "\u{1D553}",
        bot: "\u22A5",
        bottom: "\u22A5",
        bowtie: "\u22C8",
        boxbox: "\u29C9",
        boxDL: "\u2557",
        boxDl: "\u2556",
        boxdL: "\u2555",
        boxdl: "\u2510",
        boxDR: "\u2554",
        boxDr: "\u2553",
        boxdR: "\u2552",
        boxdr: "\u250C",
        boxH: "\u2550",
        boxh: "\u2500",
        boxHD: "\u2566",
        boxHd: "\u2564",
        boxhD: "\u2565",
        boxhd: "\u252C",
        boxHU: "\u2569",
        boxHu: "\u2567",
        boxhU: "\u2568",
        boxhu: "\u2534",
        boxminus: "\u229F",
        boxplus: "\u229E",
        boxtimes: "\u22A0",
        boxUL: "\u255D",
        boxUl: "\u255C",
        boxuL: "\u255B",
        boxul: "\u2518",
        boxUR: "\u255A",
        boxUr: "\u2559",
        boxuR: "\u2558",
        boxur: "\u2514",
        boxV: "\u2551",
        boxv: "\u2502",
        boxVH: "\u256C",
        boxVh: "\u256B",
        boxvH: "\u256A",
        boxvh: "\u253C",
        boxVL: "\u2563",
        boxVl: "\u2562",
        boxvL: "\u2561",
        boxvl: "\u2524",
        boxVR: "\u2560",
        boxVr: "\u255F",
        boxvR: "\u255E",
        boxvr: "\u251C",
        bprime: "\u2035",
        Breve: "\u02D8",
        breve: "\u02D8",
        brvbar: "\xA6",
        Bscr: "\u212C",
        bscr: "\u{1D4B7}",
        bsemi: "\u204F",
        bsim: "\u223D",
        bsime: "\u22CD",
        bsol: "\\",
        bsolb: "\u29C5",
        bsolhsub: "\u27C8",
        bull: "\u2022",
        bullet: "\u2022",
        bump: "\u224E",
        bumpE: "\u2AAE",
        bumpe: "\u224F",
        Bumpeq: "\u224E",
        bumpeq: "\u224F",
        Cacute: "\u0106",
        cacute: "\u0107",
        Cap: "\u22D2",
        cap: "\u2229",
        capand: "\u2A44",
        capbrcup: "\u2A49",
        capcap: "\u2A4B",
        capcup: "\u2A47",
        capdot: "\u2A40",
        CapitalDifferentialD: "\u2145",
        caps: "\u2229\uFE00",
        caret: "\u2041",
        caron: "\u02C7",
        Cayleys: "\u212D",
        ccaps: "\u2A4D",
        Ccaron: "\u010C",
        ccaron: "\u010D",
        Ccedil: "\xC7",
        ccedil: "\xE7",
        Ccirc: "\u0108",
        ccirc: "\u0109",
        Cconint: "\u2230",
        ccups: "\u2A4C",
        ccupssm: "\u2A50",
        Cdot: "\u010A",
        cdot: "\u010B",
        cedil: "\xB8",
        Cedilla: "\xB8",
        cemptyv: "\u29B2",
        cent: "\xA2",
        CenterDot: "\xB7",
        centerdot: "\xB7",
        Cfr: "\u212D",
        cfr: "\u{1D520}",
        CHcy: "\u0427",
        chcy: "\u0447",
        check: "\u2713",
        checkmark: "\u2713",
        Chi: "\u03A7",
        chi: "\u03C7",
        cir: "\u25CB",
        circ: "\u02C6",
        circeq: "\u2257",
        circlearrowleft: "\u21BA",
        circlearrowright: "\u21BB",
        circledast: "\u229B",
        circledcirc: "\u229A",
        circleddash: "\u229D",
        CircleDot: "\u2299",
        circledR: "\xAE",
        circledS: "\u24C8",
        CircleMinus: "\u2296",
        CirclePlus: "\u2295",
        CircleTimes: "\u2297",
        cirE: "\u29C3",
        cire: "\u2257",
        cirfnint: "\u2A10",
        cirmid: "\u2AEF",
        cirscir: "\u29C2",
        ClockwiseContourIntegral: "\u2232",
        CloseCurlyDoubleQuote: "\u201D",
        CloseCurlyQuote: "\u2019",
        clubs: "\u2663",
        clubsuit: "\u2663",
        Colon: "\u2237",
        colon: ":",
        Colone: "\u2A74",
        colone: "\u2254",
        coloneq: "\u2254",
        comma: ",",
        commat: "@",
        comp: "\u2201",
        compfn: "\u2218",
        complement: "\u2201",
        complexes: "\u2102",
        cong: "\u2245",
        congdot: "\u2A6D",
        Congruent: "\u2261",
        Conint: "\u222F",
        conint: "\u222E",
        ContourIntegral: "\u222E",
        Copf: "\u2102",
        copf: "\u{1D554}",
        coprod: "\u2210",
        Coproduct: "\u2210",
        COPY: "\xA9",
        copy: "\xA9",
        copysr: "\u2117",
        CounterClockwiseContourIntegral: "\u2233",
        crarr: "\u21B5",
        Cross: "\u2A2F",
        cross: "\u2717",
        Cscr: "\u{1D49E}",
        cscr: "\u{1D4B8}",
        csub: "\u2ACF",
        csube: "\u2AD1",
        csup: "\u2AD0",
        csupe: "\u2AD2",
        ctdot: "\u22EF",
        cudarrl: "\u2938",
        cudarrr: "\u2935",
        cuepr: "\u22DE",
        cuesc: "\u22DF",
        cularr: "\u21B6",
        cularrp: "\u293D",
        Cup: "\u22D3",
        cup: "\u222A",
        cupbrcap: "\u2A48",
        CupCap: "\u224D",
        cupcap: "\u2A46",
        cupcup: "\u2A4A",
        cupdot: "\u228D",
        cupor: "\u2A45",
        cups: "\u222A\uFE00",
        curarr: "\u21B7",
        curarrm: "\u293C",
        curlyeqprec: "\u22DE",
        curlyeqsucc: "\u22DF",
        curlyvee: "\u22CE",
        curlywedge: "\u22CF",
        curren: "\xA4",
        curvearrowleft: "\u21B6",
        curvearrowright: "\u21B7",
        cuvee: "\u22CE",
        cuwed: "\u22CF",
        cwconint: "\u2232",
        cwint: "\u2231",
        cylcty: "\u232D",
        Dagger: "\u2021",
        dagger: "\u2020",
        daleth: "\u2138",
        Darr: "\u21A1",
        dArr: "\u21D3",
        darr: "\u2193",
        dash: "\u2010",
        Dashv: "\u2AE4",
        dashv: "\u22A3",
        dbkarow: "\u290F",
        dblac: "\u02DD",
        Dcaron: "\u010E",
        dcaron: "\u010F",
        Dcy: "\u0414",
        dcy: "\u0434",
        DD: "\u2145",
        dd: "\u2146",
        ddagger: "\u2021",
        ddarr: "\u21CA",
        DDotrahd: "\u2911",
        ddotseq: "\u2A77",
        deg: "\xB0",
        Del: "\u2207",
        Delta: "\u0394",
        delta: "\u03B4",
        demptyv: "\u29B1",
        dfisht: "\u297F",
        Dfr: "\u{1D507}",
        dfr: "\u{1D521}",
        dHar: "\u2965",
        dharl: "\u21C3",
        dharr: "\u21C2",
        DiacriticalAcute: "\xB4",
        DiacriticalDot: "\u02D9",
        DiacriticalDoubleAcute: "\u02DD",
        DiacriticalGrave: "`",
        DiacriticalTilde: "\u02DC",
        diam: "\u22C4",
        Diamond: "\u22C4",
        diamond: "\u22C4",
        diamondsuit: "\u2666",
        diams: "\u2666",
        die: "\xA8",
        DifferentialD: "\u2146",
        digamma: "\u03DD",
        disin: "\u22F2",
        div: "\xF7",
        divide: "\xF7",
        divideontimes: "\u22C7",
        divonx: "\u22C7",
        DJcy: "\u0402",
        djcy: "\u0452",
        dlcorn: "\u231E",
        dlcrop: "\u230D",
        dollar: "$",
        Dopf: "\u{1D53B}",
        dopf: "\u{1D555}",
        Dot: "\xA8",
        dot: "\u02D9",
        DotDot: "\u20DC",
        doteq: "\u2250",
        doteqdot: "\u2251",
        DotEqual: "\u2250",
        dotminus: "\u2238",
        dotplus: "\u2214",
        dotsquare: "\u22A1",
        doublebarwedge: "\u2306",
        DoubleContourIntegral: "\u222F",
        DoubleDot: "\xA8",
        DoubleDownArrow: "\u21D3",
        DoubleLeftArrow: "\u21D0",
        DoubleLeftRightArrow: "\u21D4",
        DoubleLeftTee: "\u2AE4",
        DoubleLongLeftArrow: "\u27F8",
        DoubleLongLeftRightArrow: "\u27FA",
        DoubleLongRightArrow: "\u27F9",
        DoubleRightArrow: "\u21D2",
        DoubleRightTee: "\u22A8",
        DoubleUpArrow: "\u21D1",
        DoubleUpDownArrow: "\u21D5",
        DoubleVerticalBar: "\u2225",
        DownArrow: "\u2193",
        Downarrow: "\u21D3",
        downarrow: "\u2193",
        DownArrowBar: "\u2913",
        DownArrowUpArrow: "\u21F5",
        DownBreve: "\u0311",
        downdownarrows: "\u21CA",
        downharpoonleft: "\u21C3",
        downharpoonright: "\u21C2",
        DownLeftRightVector: "\u2950",
        DownLeftTeeVector: "\u295E",
        DownLeftVector: "\u21BD",
        DownLeftVectorBar: "\u2956",
        DownRightTeeVector: "\u295F",
        DownRightVector: "\u21C1",
        DownRightVectorBar: "\u2957",
        DownTee: "\u22A4",
        DownTeeArrow: "\u21A7",
        drbkarow: "\u2910",
        drcorn: "\u231F",
        drcrop: "\u230C",
        Dscr: "\u{1D49F}",
        dscr: "\u{1D4B9}",
        DScy: "\u0405",
        dscy: "\u0455",
        dsol: "\u29F6",
        Dstrok: "\u0110",
        dstrok: "\u0111",
        dtdot: "\u22F1",
        dtri: "\u25BF",
        dtrif: "\u25BE",
        duarr: "\u21F5",
        duhar: "\u296F",
        dwangle: "\u29A6",
        DZcy: "\u040F",
        dzcy: "\u045F",
        dzigrarr: "\u27FF",
        Eacute: "\xC9",
        eacute: "\xE9",
        easter: "\u2A6E",
        Ecaron: "\u011A",
        ecaron: "\u011B",
        ecir: "\u2256",
        Ecirc: "\xCA",
        ecirc: "\xEA",
        ecolon: "\u2255",
        Ecy: "\u042D",
        ecy: "\u044D",
        eDDot: "\u2A77",
        Edot: "\u0116",
        eDot: "\u2251",
        edot: "\u0117",
        ee: "\u2147",
        efDot: "\u2252",
        Efr: "\u{1D508}",
        efr: "\u{1D522}",
        eg: "\u2A9A",
        Egrave: "\xC8",
        egrave: "\xE8",
        egs: "\u2A96",
        egsdot: "\u2A98",
        el: "\u2A99",
        Element: "\u2208",
        elinters: "\u23E7",
        ell: "\u2113",
        els: "\u2A95",
        elsdot: "\u2A97",
        Emacr: "\u0112",
        emacr: "\u0113",
        empty: "\u2205",
        emptyset: "\u2205",
        EmptySmallSquare: "\u25FB",
        emptyv: "\u2205",
        EmptyVerySmallSquare: "\u25AB",
        emsp: "\u2003",
        emsp13: "\u2004",
        emsp14: "\u2005",
        ENG: "\u014A",
        eng: "\u014B",
        ensp: "\u2002",
        Eogon: "\u0118",
        eogon: "\u0119",
        Eopf: "\u{1D53C}",
        eopf: "\u{1D556}",
        epar: "\u22D5",
        eparsl: "\u29E3",
        eplus: "\u2A71",
        epsi: "\u03B5",
        Epsilon: "\u0395",
        epsilon: "\u03B5",
        epsiv: "\u03F5",
        eqcirc: "\u2256",
        eqcolon: "\u2255",
        eqsim: "\u2242",
        eqslantgtr: "\u2A96",
        eqslantless: "\u2A95",
        Equal: "\u2A75",
        equals: "=",
        EqualTilde: "\u2242",
        equest: "\u225F",
        Equilibrium: "\u21CC",
        equiv: "\u2261",
        equivDD: "\u2A78",
        eqvparsl: "\u29E5",
        erarr: "\u2971",
        erDot: "\u2253",
        Escr: "\u2130",
        escr: "\u212F",
        esdot: "\u2250",
        Esim: "\u2A73",
        esim: "\u2242",
        Eta: "\u0397",
        eta: "\u03B7",
        ETH: "\xD0",
        eth: "\xF0",
        Euml: "\xCB",
        euml: "\xEB",
        euro: "\u20AC",
        excl: "!",
        exist: "\u2203",
        Exists: "\u2203",
        expectation: "\u2130",
        ExponentialE: "\u2147",
        exponentiale: "\u2147",
        fallingdotseq: "\u2252",
        Fcy: "\u0424",
        fcy: "\u0444",
        female: "\u2640",
        ffilig: "\uFB03",
        fflig: "\uFB00",
        ffllig: "\uFB04",
        Ffr: "\u{1D509}",
        ffr: "\u{1D523}",
        filig: "\uFB01",
        FilledSmallSquare: "\u25FC",
        FilledVerySmallSquare: "\u25AA",
        fjlig: "fj",
        flat: "\u266D",
        fllig: "\uFB02",
        fltns: "\u25B1",
        fnof: "\u0192",
        Fopf: "\u{1D53D}",
        fopf: "\u{1D557}",
        ForAll: "\u2200",
        forall: "\u2200",
        fork: "\u22D4",
        forkv: "\u2AD9",
        Fouriertrf: "\u2131",
        fpartint: "\u2A0D",
        frac12: "\xBD",
        frac13: "\u2153",
        frac14: "\xBC",
        frac15: "\u2155",
        frac16: "\u2159",
        frac18: "\u215B",
        frac23: "\u2154",
        frac25: "\u2156",
        frac34: "\xBE",
        frac35: "\u2157",
        frac38: "\u215C",
        frac45: "\u2158",
        frac56: "\u215A",
        frac58: "\u215D",
        frac78: "\u215E",
        frasl: "\u2044",
        frown: "\u2322",
        Fscr: "\u2131",
        fscr: "\u{1D4BB}",
        gacute: "\u01F5",
        Gamma: "\u0393",
        gamma: "\u03B3",
        Gammad: "\u03DC",
        gammad: "\u03DD",
        gap: "\u2A86",
        Gbreve: "\u011E",
        gbreve: "\u011F",
        Gcedil: "\u0122",
        Gcirc: "\u011C",
        gcirc: "\u011D",
        Gcy: "\u0413",
        gcy: "\u0433",
        Gdot: "\u0120",
        gdot: "\u0121",
        gE: "\u2267",
        ge: "\u2265",
        gEl: "\u2A8C",
        gel: "\u22DB",
        geq: "\u2265",
        geqq: "\u2267",
        geqslant: "\u2A7E",
        ges: "\u2A7E",
        gescc: "\u2AA9",
        gesdot: "\u2A80",
        gesdoto: "\u2A82",
        gesdotol: "\u2A84",
        gesl: "\u22DB\uFE00",
        gesles: "\u2A94",
        Gfr: "\u{1D50A}",
        gfr: "\u{1D524}",
        Gg: "\u22D9",
        gg: "\u226B",
        ggg: "\u22D9",
        gimel: "\u2137",
        GJcy: "\u0403",
        gjcy: "\u0453",
        gl: "\u2277",
        gla: "\u2AA5",
        glE: "\u2A92",
        glj: "\u2AA4",
        gnap: "\u2A8A",
        gnapprox: "\u2A8A",
        gnE: "\u2269",
        gne: "\u2A88",
        gneq: "\u2A88",
        gneqq: "\u2269",
        gnsim: "\u22E7",
        Gopf: "\u{1D53E}",
        gopf: "\u{1D558}",
        grave: "`",
        GreaterEqual: "\u2265",
        GreaterEqualLess: "\u22DB",
        GreaterFullEqual: "\u2267",
        GreaterGreater: "\u2AA2",
        GreaterLess: "\u2277",
        GreaterSlantEqual: "\u2A7E",
        GreaterTilde: "\u2273",
        Gscr: "\u{1D4A2}",
        gscr: "\u210A",
        gsim: "\u2273",
        gsime: "\u2A8E",
        gsiml: "\u2A90",
        Gt: "\u226B",
        GT: ">",
        gt: ">",
        gtcc: "\u2AA7",
        gtcir: "\u2A7A",
        gtdot: "\u22D7",
        gtlPar: "\u2995",
        gtquest: "\u2A7C",
        gtrapprox: "\u2A86",
        gtrarr: "\u2978",
        gtrdot: "\u22D7",
        gtreqless: "\u22DB",
        gtreqqless: "\u2A8C",
        gtrless: "\u2277",
        gtrsim: "\u2273",
        gvertneqq: "\u2269\uFE00",
        gvnE: "\u2269\uFE00",
        Hacek: "\u02C7",
        hairsp: "\u200A",
        half: "\xBD",
        hamilt: "\u210B",
        HARDcy: "\u042A",
        hardcy: "\u044A",
        hArr: "\u21D4",
        harr: "\u2194",
        harrcir: "\u2948",
        harrw: "\u21AD",
        Hat: "^",
        hbar: "\u210F",
        Hcirc: "\u0124",
        hcirc: "\u0125",
        hearts: "\u2665",
        heartsuit: "\u2665",
        hellip: "\u2026",
        hercon: "\u22B9",
        Hfr: "\u210C",
        hfr: "\u{1D525}",
        HilbertSpace: "\u210B",
        hksearow: "\u2925",
        hkswarow: "\u2926",
        hoarr: "\u21FF",
        homtht: "\u223B",
        hookleftarrow: "\u21A9",
        hookrightarrow: "\u21AA",
        Hopf: "\u210D",
        hopf: "\u{1D559}",
        horbar: "\u2015",
        HorizontalLine: "\u2500",
        Hscr: "\u210B",
        hscr: "\u{1D4BD}",
        hslash: "\u210F",
        Hstrok: "\u0126",
        hstrok: "\u0127",
        HumpDownHump: "\u224E",
        HumpEqual: "\u224F",
        hybull: "\u2043",
        hyphen: "\u2010",
        Iacute: "\xCD",
        iacute: "\xED",
        ic: "\u2063",
        Icirc: "\xCE",
        icirc: "\xEE",
        Icy: "\u0418",
        icy: "\u0438",
        Idot: "\u0130",
        IEcy: "\u0415",
        iecy: "\u0435",
        iexcl: "\xA1",
        iff: "\u21D4",
        Ifr: "\u2111",
        ifr: "\u{1D526}",
        Igrave: "\xCC",
        igrave: "\xEC",
        ii: "\u2148",
        iiiint: "\u2A0C",
        iiint: "\u222D",
        iinfin: "\u29DC",
        iiota: "\u2129",
        IJlig: "\u0132",
        ijlig: "\u0133",
        Im: "\u2111",
        Imacr: "\u012A",
        imacr: "\u012B",
        image: "\u2111",
        ImaginaryI: "\u2148",
        imagline: "\u2110",
        imagpart: "\u2111",
        imath: "\u0131",
        imof: "\u22B7",
        imped: "\u01B5",
        Implies: "\u21D2",
        in: "\u2208",
        incare: "\u2105",
        infin: "\u221E",
        infintie: "\u29DD",
        inodot: "\u0131",
        Int: "\u222C",
        int: "\u222B",
        intcal: "\u22BA",
        integers: "\u2124",
        Integral: "\u222B",
        intercal: "\u22BA",
        Intersection: "\u22C2",
        intlarhk: "\u2A17",
        intprod: "\u2A3C",
        InvisibleComma: "\u2063",
        InvisibleTimes: "\u2062",
        IOcy: "\u0401",
        iocy: "\u0451",
        Iogon: "\u012E",
        iogon: "\u012F",
        Iopf: "\u{1D540}",
        iopf: "\u{1D55A}",
        Iota: "\u0399",
        iota: "\u03B9",
        iprod: "\u2A3C",
        iquest: "\xBF",
        Iscr: "\u2110",
        iscr: "\u{1D4BE}",
        isin: "\u2208",
        isindot: "\u22F5",
        isinE: "\u22F9",
        isins: "\u22F4",
        isinsv: "\u22F3",
        isinv: "\u2208",
        it: "\u2062",
        Itilde: "\u0128",
        itilde: "\u0129",
        Iukcy: "\u0406",
        iukcy: "\u0456",
        Iuml: "\xCF",
        iuml: "\xEF",
        Jcirc: "\u0134",
        jcirc: "\u0135",
        Jcy: "\u0419",
        jcy: "\u0439",
        Jfr: "\u{1D50D}",
        jfr: "\u{1D527}",
        jmath: "\u0237",
        Jopf: "\u{1D541}",
        jopf: "\u{1D55B}",
        Jscr: "\u{1D4A5}",
        jscr: "\u{1D4BF}",
        Jsercy: "\u0408",
        jsercy: "\u0458",
        Jukcy: "\u0404",
        jukcy: "\u0454",
        Kappa: "\u039A",
        kappa: "\u03BA",
        kappav: "\u03F0",
        Kcedil: "\u0136",
        kcedil: "\u0137",
        Kcy: "\u041A",
        kcy: "\u043A",
        Kfr: "\u{1D50E}",
        kfr: "\u{1D528}",
        kgreen: "\u0138",
        KHcy: "\u0425",
        khcy: "\u0445",
        KJcy: "\u040C",
        kjcy: "\u045C",
        Kopf: "\u{1D542}",
        kopf: "\u{1D55C}",
        Kscr: "\u{1D4A6}",
        kscr: "\u{1D4C0}",
        lAarr: "\u21DA",
        Lacute: "\u0139",
        lacute: "\u013A",
        laemptyv: "\u29B4",
        lagran: "\u2112",
        Lambda: "\u039B",
        lambda: "\u03BB",
        Lang: "\u27EA",
        lang: "\u27E8",
        langd: "\u2991",
        langle: "\u27E8",
        lap: "\u2A85",
        Laplacetrf: "\u2112",
        laquo: "\xAB",
        Larr: "\u219E",
        lArr: "\u21D0",
        larr: "\u2190",
        larrb: "\u21E4",
        larrbfs: "\u291F",
        larrfs: "\u291D",
        larrhk: "\u21A9",
        larrlp: "\u21AB",
        larrpl: "\u2939",
        larrsim: "\u2973",
        larrtl: "\u21A2",
        lat: "\u2AAB",
        lAtail: "\u291B",
        latail: "\u2919",
        late: "\u2AAD",
        lates: "\u2AAD\uFE00",
        lBarr: "\u290E",
        lbarr: "\u290C",
        lbbrk: "\u2772",
        lbrace: "{",
        lbrack: "[",
        lbrke: "\u298B",
        lbrksld: "\u298F",
        lbrkslu: "\u298D",
        Lcaron: "\u013D",
        lcaron: "\u013E",
        Lcedil: "\u013B",
        lcedil: "\u013C",
        lceil: "\u2308",
        lcub: "{",
        Lcy: "\u041B",
        lcy: "\u043B",
        ldca: "\u2936",
        ldquo: "\u201C",
        ldquor: "\u201E",
        ldrdhar: "\u2967",
        ldrushar: "\u294B",
        ldsh: "\u21B2",
        lE: "\u2266",
        le: "\u2264",
        LeftAngleBracket: "\u27E8",
        LeftArrow: "\u2190",
        Leftarrow: "\u21D0",
        leftarrow: "\u2190",
        LeftArrowBar: "\u21E4",
        LeftArrowRightArrow: "\u21C6",
        leftarrowtail: "\u21A2",
        LeftCeiling: "\u2308",
        LeftDoubleBracket: "\u27E6",
        LeftDownTeeVector: "\u2961",
        LeftDownVector: "\u21C3",
        LeftDownVectorBar: "\u2959",
        LeftFloor: "\u230A",
        leftharpoondown: "\u21BD",
        leftharpoonup: "\u21BC",
        leftleftarrows: "\u21C7",
        LeftRightArrow: "\u2194",
        Leftrightarrow: "\u21D4",
        leftrightarrow: "\u2194",
        leftrightarrows: "\u21C6",
        leftrightharpoons: "\u21CB",
        leftrightsquigarrow: "\u21AD",
        LeftRightVector: "\u294E",
        LeftTee: "\u22A3",
        LeftTeeArrow: "\u21A4",
        LeftTeeVector: "\u295A",
        leftthreetimes: "\u22CB",
        LeftTriangle: "\u22B2",
        LeftTriangleBar: "\u29CF",
        LeftTriangleEqual: "\u22B4",
        LeftUpDownVector: "\u2951",
        LeftUpTeeVector: "\u2960",
        LeftUpVector: "\u21BF",
        LeftUpVectorBar: "\u2958",
        LeftVector: "\u21BC",
        LeftVectorBar: "\u2952",
        lEg: "\u2A8B",
        leg: "\u22DA",
        leq: "\u2264",
        leqq: "\u2266",
        leqslant: "\u2A7D",
        les: "\u2A7D",
        lescc: "\u2AA8",
        lesdot: "\u2A7F",
        lesdoto: "\u2A81",
        lesdotor: "\u2A83",
        lesg: "\u22DA\uFE00",
        lesges: "\u2A93",
        lessapprox: "\u2A85",
        lessdot: "\u22D6",
        lesseqgtr: "\u22DA",
        lesseqqgtr: "\u2A8B",
        LessEqualGreater: "\u22DA",
        LessFullEqual: "\u2266",
        LessGreater: "\u2276",
        lessgtr: "\u2276",
        LessLess: "\u2AA1",
        lesssim: "\u2272",
        LessSlantEqual: "\u2A7D",
        LessTilde: "\u2272",
        lfisht: "\u297C",
        lfloor: "\u230A",
        Lfr: "\u{1D50F}",
        lfr: "\u{1D529}",
        lg: "\u2276",
        lgE: "\u2A91",
        lHar: "\u2962",
        lhard: "\u21BD",
        lharu: "\u21BC",
        lharul: "\u296A",
        lhblk: "\u2584",
        LJcy: "\u0409",
        ljcy: "\u0459",
        Ll: "\u22D8",
        ll: "\u226A",
        llarr: "\u21C7",
        llcorner: "\u231E",
        Lleftarrow: "\u21DA",
        llhard: "\u296B",
        lltri: "\u25FA",
        Lmidot: "\u013F",
        lmidot: "\u0140",
        lmoust: "\u23B0",
        lmoustache: "\u23B0",
        lnap: "\u2A89",
        lnapprox: "\u2A89",
        lnE: "\u2268",
        lne: "\u2A87",
        lneq: "\u2A87",
        lneqq: "\u2268",
        lnsim: "\u22E6",
        loang: "\u27EC",
        loarr: "\u21FD",
        lobrk: "\u27E6",
        LongLeftArrow: "\u27F5",
        Longleftarrow: "\u27F8",
        longleftarrow: "\u27F5",
        LongLeftRightArrow: "\u27F7",
        Longleftrightarrow: "\u27FA",
        longleftrightarrow: "\u27F7",
        longmapsto: "\u27FC",
        LongRightArrow: "\u27F6",
        Longrightarrow: "\u27F9",
        longrightarrow: "\u27F6",
        looparrowleft: "\u21AB",
        looparrowright: "\u21AC",
        lopar: "\u2985",
        Lopf: "\u{1D543}",
        lopf: "\u{1D55D}",
        loplus: "\u2A2D",
        lotimes: "\u2A34",
        lowast: "\u2217",
        lowbar: "_",
        LowerLeftArrow: "\u2199",
        LowerRightArrow: "\u2198",
        loz: "\u25CA",
        lozenge: "\u25CA",
        lozf: "\u29EB",
        lpar: "(",
        lparlt: "\u2993",
        lrarr: "\u21C6",
        lrcorner: "\u231F",
        lrhar: "\u21CB",
        lrhard: "\u296D",
        lrm: "\u200E",
        lrtri: "\u22BF",
        lsaquo: "\u2039",
        Lscr: "\u2112",
        lscr: "\u{1D4C1}",
        Lsh: "\u21B0",
        lsh: "\u21B0",
        lsim: "\u2272",
        lsime: "\u2A8D",
        lsimg: "\u2A8F",
        lsqb: "[",
        lsquo: "\u2018",
        lsquor: "\u201A",
        Lstrok: "\u0141",
        lstrok: "\u0142",
        Lt: "\u226A",
        LT: "<",
        lt: "<",
        ltcc: "\u2AA6",
        ltcir: "\u2A79",
        ltdot: "\u22D6",
        lthree: "\u22CB",
        ltimes: "\u22C9",
        ltlarr: "\u2976",
        ltquest: "\u2A7B",
        ltri: "\u25C3",
        ltrie: "\u22B4",
        ltrif: "\u25C2",
        ltrPar: "\u2996",
        lurdshar: "\u294A",
        luruhar: "\u2966",
        lvertneqq: "\u2268\uFE00",
        lvnE: "\u2268\uFE00",
        macr: "\xAF",
        male: "\u2642",
        malt: "\u2720",
        maltese: "\u2720",
        Map: "\u2905",
        map: "\u21A6",
        mapsto: "\u21A6",
        mapstodown: "\u21A7",
        mapstoleft: "\u21A4",
        mapstoup: "\u21A5",
        marker: "\u25AE",
        mcomma: "\u2A29",
        Mcy: "\u041C",
        mcy: "\u043C",
        mdash: "\u2014",
        mDDot: "\u223A",
        measuredangle: "\u2221",
        MediumSpace: "\u205F",
        Mellintrf: "\u2133",
        Mfr: "\u{1D510}",
        mfr: "\u{1D52A}",
        mho: "\u2127",
        micro: "\xB5",
        mid: "\u2223",
        midast: "*",
        midcir: "\u2AF0",
        middot: "\xB7",
        minus: "\u2212",
        minusb: "\u229F",
        minusd: "\u2238",
        minusdu: "\u2A2A",
        MinusPlus: "\u2213",
        mlcp: "\u2ADB",
        mldr: "\u2026",
        mnplus: "\u2213",
        models: "\u22A7",
        Mopf: "\u{1D544}",
        mopf: "\u{1D55E}",
        mp: "\u2213",
        Mscr: "\u2133",
        mscr: "\u{1D4C2}",
        mstpos: "\u223E",
        Mu: "\u039C",
        mu: "\u03BC",
        multimap: "\u22B8",
        mumap: "\u22B8",
        nabla: "\u2207",
        Nacute: "\u0143",
        nacute: "\u0144",
        nang: "\u2220\u20D2",
        nap: "\u2249",
        napE: "\u2A70\u0338",
        napid: "\u224B\u0338",
        napos: "\u0149",
        napprox: "\u2249",
        natur: "\u266E",
        natural: "\u266E",
        naturals: "\u2115",
        nbsp: "\xA0",
        nbump: "\u224E\u0338",
        nbumpe: "\u224F\u0338",
        ncap: "\u2A43",
        Ncaron: "\u0147",
        ncaron: "\u0148",
        Ncedil: "\u0145",
        ncedil: "\u0146",
        ncong: "\u2247",
        ncongdot: "\u2A6D\u0338",
        ncup: "\u2A42",
        Ncy: "\u041D",
        ncy: "\u043D",
        ndash: "\u2013",
        ne: "\u2260",
        nearhk: "\u2924",
        neArr: "\u21D7",
        nearr: "\u2197",
        nearrow: "\u2197",
        nedot: "\u2250\u0338",
        NegativeMediumSpace: "\u200B",
        NegativeThickSpace: "\u200B",
        NegativeThinSpace: "\u200B",
        NegativeVeryThinSpace: "\u200B",
        nequiv: "\u2262",
        nesear: "\u2928",
        nesim: "\u2242\u0338",
        NestedGreaterGreater: "\u226B",
        NestedLessLess: "\u226A",
        NewLine: "\n",
        nexist: "\u2204",
        nexists: "\u2204",
        Nfr: "\u{1D511}",
        nfr: "\u{1D52B}",
        ngE: "\u2267\u0338",
        nge: "\u2271",
        ngeq: "\u2271",
        ngeqq: "\u2267\u0338",
        ngeqslant: "\u2A7E\u0338",
        nges: "\u2A7E\u0338",
        nGg: "\u22D9\u0338",
        ngsim: "\u2275",
        nGt: "\u226B\u20D2",
        ngt: "\u226F",
        ngtr: "\u226F",
        nGtv: "\u226B\u0338",
        nhArr: "\u21CE",
        nharr: "\u21AE",
        nhpar: "\u2AF2",
        ni: "\u220B",
        nis: "\u22FC",
        nisd: "\u22FA",
        niv: "\u220B",
        NJcy: "\u040A",
        njcy: "\u045A",
        nlArr: "\u21CD",
        nlarr: "\u219A",
        nldr: "\u2025",
        nlE: "\u2266\u0338",
        nle: "\u2270",
        nLeftarrow: "\u21CD",
        nleftarrow: "\u219A",
        nLeftrightarrow: "\u21CE",
        nleftrightarrow: "\u21AE",
        nleq: "\u2270",
        nleqq: "\u2266\u0338",
        nleqslant: "\u2A7D\u0338",
        nles: "\u2A7D\u0338",
        nless: "\u226E",
        nLl: "\u22D8\u0338",
        nlsim: "\u2274",
        nLt: "\u226A\u20D2",
        nlt: "\u226E",
        nltri: "\u22EA",
        nltrie: "\u22EC",
        nLtv: "\u226A\u0338",
        nmid: "\u2224",
        NoBreak: "\u2060",
        NonBreakingSpace: "\xA0",
        Nopf: "\u2115",
        nopf: "\u{1D55F}",
        Not: "\u2AEC",
        not: "\xAC",
        NotCongruent: "\u2262",
        NotCupCap: "\u226D",
        NotDoubleVerticalBar: "\u2226",
        NotElement: "\u2209",
        NotEqual: "\u2260",
        NotEqualTilde: "\u2242\u0338",
        NotExists: "\u2204",
        NotGreater: "\u226F",
        NotGreaterEqual: "\u2271",
        NotGreaterFullEqual: "\u2267\u0338",
        NotGreaterGreater: "\u226B\u0338",
        NotGreaterLess: "\u2279",
        NotGreaterSlantEqual: "\u2A7E\u0338",
        NotGreaterTilde: "\u2275",
        NotHumpDownHump: "\u224E\u0338",
        NotHumpEqual: "\u224F\u0338",
        notin: "\u2209",
        notindot: "\u22F5\u0338",
        notinE: "\u22F9\u0338",
        notinva: "\u2209",
        notinvb: "\u22F7",
        notinvc: "\u22F6",
        NotLeftTriangle: "\u22EA",
        NotLeftTriangleBar: "\u29CF\u0338",
        NotLeftTriangleEqual: "\u22EC",
        NotLess: "\u226E",
        NotLessEqual: "\u2270",
        NotLessGreater: "\u2278",
        NotLessLess: "\u226A\u0338",
        NotLessSlantEqual: "\u2A7D\u0338",
        NotLessTilde: "\u2274",
        NotNestedGreaterGreater: "\u2AA2\u0338",
        NotNestedLessLess: "\u2AA1\u0338",
        notni: "\u220C",
        notniva: "\u220C",
        notnivb: "\u22FE",
        notnivc: "\u22FD",
        NotPrecedes: "\u2280",
        NotPrecedesEqual: "\u2AAF\u0338",
        NotPrecedesSlantEqual: "\u22E0",
        NotReverseElement: "\u220C",
        NotRightTriangle: "\u22EB",
        NotRightTriangleBar: "\u29D0\u0338",
        NotRightTriangleEqual: "\u22ED",
        NotSquareSubset: "\u228F\u0338",
        NotSquareSubsetEqual: "\u22E2",
        NotSquareSuperset: "\u2290\u0338",
        NotSquareSupersetEqual: "\u22E3",
        NotSubset: "\u2282\u20D2",
        NotSubsetEqual: "\u2288",
        NotSucceeds: "\u2281",
        NotSucceedsEqual: "\u2AB0\u0338",
        NotSucceedsSlantEqual: "\u22E1",
        NotSucceedsTilde: "\u227F\u0338",
        NotSuperset: "\u2283\u20D2",
        NotSupersetEqual: "\u2289",
        NotTilde: "\u2241",
        NotTildeEqual: "\u2244",
        NotTildeFullEqual: "\u2247",
        NotTildeTilde: "\u2249",
        NotVerticalBar: "\u2224",
        npar: "\u2226",
        nparallel: "\u2226",
        nparsl: "\u2AFD\u20E5",
        npart: "\u2202\u0338",
        npolint: "\u2A14",
        npr: "\u2280",
        nprcue: "\u22E0",
        npre: "\u2AAF\u0338",
        nprec: "\u2280",
        npreceq: "\u2AAF\u0338",
        nrArr: "\u21CF",
        nrarr: "\u219B",
        nrarrc: "\u2933\u0338",
        nrarrw: "\u219D\u0338",
        nRightarrow: "\u21CF",
        nrightarrow: "\u219B",
        nrtri: "\u22EB",
        nrtrie: "\u22ED",
        nsc: "\u2281",
        nsccue: "\u22E1",
        nsce: "\u2AB0\u0338",
        Nscr: "\u{1D4A9}",
        nscr: "\u{1D4C3}",
        nshortmid: "\u2224",
        nshortparallel: "\u2226",
        nsim: "\u2241",
        nsime: "\u2244",
        nsimeq: "\u2244",
        nsmid: "\u2224",
        nspar: "\u2226",
        nsqsube: "\u22E2",
        nsqsupe: "\u22E3",
        nsub: "\u2284",
        nsubE: "\u2AC5\u0338",
        nsube: "\u2288",
        nsubset: "\u2282\u20D2",
        nsubseteq: "\u2288",
        nsubseteqq: "\u2AC5\u0338",
        nsucc: "\u2281",
        nsucceq: "\u2AB0\u0338",
        nsup: "\u2285",
        nsupE: "\u2AC6\u0338",
        nsupe: "\u2289",
        nsupset: "\u2283\u20D2",
        nsupseteq: "\u2289",
        nsupseteqq: "\u2AC6\u0338",
        ntgl: "\u2279",
        Ntilde: "\xD1",
        ntilde: "\xF1",
        ntlg: "\u2278",
        ntriangleleft: "\u22EA",
        ntrianglelefteq: "\u22EC",
        ntriangleright: "\u22EB",
        ntrianglerighteq: "\u22ED",
        Nu: "\u039D",
        nu: "\u03BD",
        num: "#",
        numero: "\u2116",
        numsp: "\u2007",
        nvap: "\u224D\u20D2",
        nVDash: "\u22AF",
        nVdash: "\u22AE",
        nvDash: "\u22AD",
        nvdash: "\u22AC",
        nvge: "\u2265\u20D2",
        nvgt: ">\u20D2",
        nvHarr: "\u2904",
        nvinfin: "\u29DE",
        nvlArr: "\u2902",
        nvle: "\u2264\u20D2",
        nvlt: "<\u20D2",
        nvltrie: "\u22B4\u20D2",
        nvrArr: "\u2903",
        nvrtrie: "\u22B5\u20D2",
        nvsim: "\u223C\u20D2",
        nwarhk: "\u2923",
        nwArr: "\u21D6",
        nwarr: "\u2196",
        nwarrow: "\u2196",
        nwnear: "\u2927",
        Oacute: "\xD3",
        oacute: "\xF3",
        oast: "\u229B",
        ocir: "\u229A",
        Ocirc: "\xD4",
        ocirc: "\xF4",
        Ocy: "\u041E",
        ocy: "\u043E",
        odash: "\u229D",
        Odblac: "\u0150",
        odblac: "\u0151",
        odiv: "\u2A38",
        odot: "\u2299",
        odsold: "\u29BC",
        OElig: "\u0152",
        oelig: "\u0153",
        ofcir: "\u29BF",
        Ofr: "\u{1D512}",
        ofr: "\u{1D52C}",
        ogon: "\u02DB",
        Ograve: "\xD2",
        ograve: "\xF2",
        ogt: "\u29C1",
        ohbar: "\u29B5",
        ohm: "\u03A9",
        oint: "\u222E",
        olarr: "\u21BA",
        olcir: "\u29BE",
        olcross: "\u29BB",
        oline: "\u203E",
        olt: "\u29C0",
        Omacr: "\u014C",
        omacr: "\u014D",
        Omega: "\u03A9",
        omega: "\u03C9",
        Omicron: "\u039F",
        omicron: "\u03BF",
        omid: "\u29B6",
        ominus: "\u2296",
        Oopf: "\u{1D546}",
        oopf: "\u{1D560}",
        opar: "\u29B7",
        OpenCurlyDoubleQuote: "\u201C",
        OpenCurlyQuote: "\u2018",
        operp: "\u29B9",
        oplus: "\u2295",
        Or: "\u2A54",
        or: "\u2228",
        orarr: "\u21BB",
        ord: "\u2A5D",
        order: "\u2134",
        orderof: "\u2134",
        ordf: "\xAA",
        ordm: "\xBA",
        origof: "\u22B6",
        oror: "\u2A56",
        orslope: "\u2A57",
        orv: "\u2A5B",
        oS: "\u24C8",
        Oscr: "\u{1D4AA}",
        oscr: "\u2134",
        Oslash: "\xD8",
        oslash: "\xF8",
        osol: "\u2298",
        Otilde: "\xD5",
        otilde: "\xF5",
        Otimes: "\u2A37",
        otimes: "\u2297",
        otimesas: "\u2A36",
        Ouml: "\xD6",
        ouml: "\xF6",
        ovbar: "\u233D",
        OverBar: "\u203E",
        OverBrace: "\u23DE",
        OverBracket: "\u23B4",
        OverParenthesis: "\u23DC",
        par: "\u2225",
        para: "\xB6",
        parallel: "\u2225",
        parsim: "\u2AF3",
        parsl: "\u2AFD",
        part: "\u2202",
        PartialD: "\u2202",
        Pcy: "\u041F",
        pcy: "\u043F",
        percnt: "%",
        period: ".",
        permil: "\u2030",
        perp: "\u22A5",
        pertenk: "\u2031",
        Pfr: "\u{1D513}",
        pfr: "\u{1D52D}",
        Phi: "\u03A6",
        phi: "\u03C6",
        phiv: "\u03D5",
        phmmat: "\u2133",
        phone: "\u260E",
        Pi: "\u03A0",
        pi: "\u03C0",
        pitchfork: "\u22D4",
        piv: "\u03D6",
        planck: "\u210F",
        planckh: "\u210E",
        plankv: "\u210F",
        plus: "+",
        plusacir: "\u2A23",
        plusb: "\u229E",
        pluscir: "\u2A22",
        plusdo: "\u2214",
        plusdu: "\u2A25",
        pluse: "\u2A72",
        PlusMinus: "\xB1",
        plusmn: "\xB1",
        plussim: "\u2A26",
        plustwo: "\u2A27",
        pm: "\xB1",
        Poincareplane: "\u210C",
        pointint: "\u2A15",
        Popf: "\u2119",
        popf: "\u{1D561}",
        pound: "\xA3",
        Pr: "\u2ABB",
        pr: "\u227A",
        prap: "\u2AB7",
        prcue: "\u227C",
        prE: "\u2AB3",
        pre: "\u2AAF",
        prec: "\u227A",
        precapprox: "\u2AB7",
        preccurlyeq: "\u227C",
        Precedes: "\u227A",
        PrecedesEqual: "\u2AAF",
        PrecedesSlantEqual: "\u227C",
        PrecedesTilde: "\u227E",
        preceq: "\u2AAF",
        precnapprox: "\u2AB9",
        precneqq: "\u2AB5",
        precnsim: "\u22E8",
        precsim: "\u227E",
        Prime: "\u2033",
        prime: "\u2032",
        primes: "\u2119",
        prnap: "\u2AB9",
        prnE: "\u2AB5",
        prnsim: "\u22E8",
        prod: "\u220F",
        Product: "\u220F",
        profalar: "\u232E",
        profline: "\u2312",
        profsurf: "\u2313",
        prop: "\u221D",
        Proportion: "\u2237",
        Proportional: "\u221D",
        propto: "\u221D",
        prsim: "\u227E",
        prurel: "\u22B0",
        Pscr: "\u{1D4AB}",
        pscr: "\u{1D4C5}",
        Psi: "\u03A8",
        psi: "\u03C8",
        puncsp: "\u2008",
        Qfr: "\u{1D514}",
        qfr: "\u{1D52E}",
        qint: "\u2A0C",
        Qopf: "\u211A",
        qopf: "\u{1D562}",
        qprime: "\u2057",
        Qscr: "\u{1D4AC}",
        qscr: "\u{1D4C6}",
        quaternions: "\u210D",
        quatint: "\u2A16",
        quest: "?",
        questeq: "\u225F",
        QUOT: '"',
        quot: '"',
        rAarr: "\u21DB",
        race: "\u223D\u0331",
        Racute: "\u0154",
        racute: "\u0155",
        radic: "\u221A",
        raemptyv: "\u29B3",
        Rang: "\u27EB",
        rang: "\u27E9",
        rangd: "\u2992",
        range: "\u29A5",
        rangle: "\u27E9",
        raquo: "\xBB",
        Rarr: "\u21A0",
        rArr: "\u21D2",
        rarr: "\u2192",
        rarrap: "\u2975",
        rarrb: "\u21E5",
        rarrbfs: "\u2920",
        rarrc: "\u2933",
        rarrfs: "\u291E",
        rarrhk: "\u21AA",
        rarrlp: "\u21AC",
        rarrpl: "\u2945",
        rarrsim: "\u2974",
        Rarrtl: "\u2916",
        rarrtl: "\u21A3",
        rarrw: "\u219D",
        rAtail: "\u291C",
        ratail: "\u291A",
        ratio: "\u2236",
        rationals: "\u211A",
        RBarr: "\u2910",
        rBarr: "\u290F",
        rbarr: "\u290D",
        rbbrk: "\u2773",
        rbrace: "}",
        rbrack: "]",
        rbrke: "\u298C",
        rbrksld: "\u298E",
        rbrkslu: "\u2990",
        Rcaron: "\u0158",
        rcaron: "\u0159",
        Rcedil: "\u0156",
        rcedil: "\u0157",
        rceil: "\u2309",
        rcub: "}",
        Rcy: "\u0420",
        rcy: "\u0440",
        rdca: "\u2937",
        rdldhar: "\u2969",
        rdquo: "\u201D",
        rdquor: "\u201D",
        rdsh: "\u21B3",
        Re: "\u211C",
        real: "\u211C",
        realine: "\u211B",
        realpart: "\u211C",
        reals: "\u211D",
        rect: "\u25AD",
        REG: "\xAE",
        reg: "\xAE",
        ReverseElement: "\u220B",
        ReverseEquilibrium: "\u21CB",
        ReverseUpEquilibrium: "\u296F",
        rfisht: "\u297D",
        rfloor: "\u230B",
        Rfr: "\u211C",
        rfr: "\u{1D52F}",
        rHar: "\u2964",
        rhard: "\u21C1",
        rharu: "\u21C0",
        rharul: "\u296C",
        Rho: "\u03A1",
        rho: "\u03C1",
        rhov: "\u03F1",
        RightAngleBracket: "\u27E9",
        RightArrow: "\u2192",
        Rightarrow: "\u21D2",
        rightarrow: "\u2192",
        RightArrowBar: "\u21E5",
        RightArrowLeftArrow: "\u21C4",
        rightarrowtail: "\u21A3",
        RightCeiling: "\u2309",
        RightDoubleBracket: "\u27E7",
        RightDownTeeVector: "\u295D",
        RightDownVector: "\u21C2",
        RightDownVectorBar: "\u2955",
        RightFloor: "\u230B",
        rightharpoondown: "\u21C1",
        rightharpoonup: "\u21C0",
        rightleftarrows: "\u21C4",
        rightleftharpoons: "\u21CC",
        rightrightarrows: "\u21C9",
        rightsquigarrow: "\u219D",
        RightTee: "\u22A2",
        RightTeeArrow: "\u21A6",
        RightTeeVector: "\u295B",
        rightthreetimes: "\u22CC",
        RightTriangle: "\u22B3",
        RightTriangleBar: "\u29D0",
        RightTriangleEqual: "\u22B5",
        RightUpDownVector: "\u294F",
        RightUpTeeVector: "\u295C",
        RightUpVector: "\u21BE",
        RightUpVectorBar: "\u2954",
        RightVector: "\u21C0",
        RightVectorBar: "\u2953",
        ring: "\u02DA",
        risingdotseq: "\u2253",
        rlarr: "\u21C4",
        rlhar: "\u21CC",
        rlm: "\u200F",
        rmoust: "\u23B1",
        rmoustache: "\u23B1",
        rnmid: "\u2AEE",
        roang: "\u27ED",
        roarr: "\u21FE",
        robrk: "\u27E7",
        ropar: "\u2986",
        Ropf: "\u211D",
        ropf: "\u{1D563}",
        roplus: "\u2A2E",
        rotimes: "\u2A35",
        RoundImplies: "\u2970",
        rpar: ")",
        rpargt: "\u2994",
        rppolint: "\u2A12",
        rrarr: "\u21C9",
        Rrightarrow: "\u21DB",
        rsaquo: "\u203A",
        Rscr: "\u211B",
        rscr: "\u{1D4C7}",
        Rsh: "\u21B1",
        rsh: "\u21B1",
        rsqb: "]",
        rsquo: "\u2019",
        rsquor: "\u2019",
        rthree: "\u22CC",
        rtimes: "\u22CA",
        rtri: "\u25B9",
        rtrie: "\u22B5",
        rtrif: "\u25B8",
        rtriltri: "\u29CE",
        RuleDelayed: "\u29F4",
        ruluhar: "\u2968",
        rx: "\u211E",
        Sacute: "\u015A",
        sacute: "\u015B",
        sbquo: "\u201A",
        Sc: "\u2ABC",
        sc: "\u227B",
        scap: "\u2AB8",
        Scaron: "\u0160",
        scaron: "\u0161",
        sccue: "\u227D",
        scE: "\u2AB4",
        sce: "\u2AB0",
        Scedil: "\u015E",
        scedil: "\u015F",
        Scirc: "\u015C",
        scirc: "\u015D",
        scnap: "\u2ABA",
        scnE: "\u2AB6",
        scnsim: "\u22E9",
        scpolint: "\u2A13",
        scsim: "\u227F",
        Scy: "\u0421",
        scy: "\u0441",
        sdot: "\u22C5",
        sdotb: "\u22A1",
        sdote: "\u2A66",
        searhk: "\u2925",
        seArr: "\u21D8",
        searr: "\u2198",
        searrow: "\u2198",
        sect: "\xA7",
        semi: ";",
        seswar: "\u2929",
        setminus: "\u2216",
        setmn: "\u2216",
        sext: "\u2736",
        Sfr: "\u{1D516}",
        sfr: "\u{1D530}",
        sfrown: "\u2322",
        sharp: "\u266F",
        SHCHcy: "\u0429",
        shchcy: "\u0449",
        SHcy: "\u0428",
        shcy: "\u0448",
        ShortDownArrow: "\u2193",
        ShortLeftArrow: "\u2190",
        shortmid: "\u2223",
        shortparallel: "\u2225",
        ShortRightArrow: "\u2192",
        ShortUpArrow: "\u2191",
        shy: "\xAD",
        Sigma: "\u03A3",
        sigma: "\u03C3",
        sigmaf: "\u03C2",
        sigmav: "\u03C2",
        sim: "\u223C",
        simdot: "\u2A6A",
        sime: "\u2243",
        simeq: "\u2243",
        simg: "\u2A9E",
        simgE: "\u2AA0",
        siml: "\u2A9D",
        simlE: "\u2A9F",
        simne: "\u2246",
        simplus: "\u2A24",
        simrarr: "\u2972",
        slarr: "\u2190",
        SmallCircle: "\u2218",
        smallsetminus: "\u2216",
        smashp: "\u2A33",
        smeparsl: "\u29E4",
        smid: "\u2223",
        smile: "\u2323",
        smt: "\u2AAA",
        smte: "\u2AAC",
        smtes: "\u2AAC\uFE00",
        SOFTcy: "\u042C",
        softcy: "\u044C",
        sol: "/",
        solb: "\u29C4",
        solbar: "\u233F",
        Sopf: "\u{1D54A}",
        sopf: "\u{1D564}",
        spades: "\u2660",
        spadesuit: "\u2660",
        spar: "\u2225",
        sqcap: "\u2293",
        sqcaps: "\u2293\uFE00",
        sqcup: "\u2294",
        sqcups: "\u2294\uFE00",
        Sqrt: "\u221A",
        sqsub: "\u228F",
        sqsube: "\u2291",
        sqsubset: "\u228F",
        sqsubseteq: "\u2291",
        sqsup: "\u2290",
        sqsupe: "\u2292",
        sqsupset: "\u2290",
        sqsupseteq: "\u2292",
        squ: "\u25A1",
        Square: "\u25A1",
        square: "\u25A1",
        SquareIntersection: "\u2293",
        SquareSubset: "\u228F",
        SquareSubsetEqual: "\u2291",
        SquareSuperset: "\u2290",
        SquareSupersetEqual: "\u2292",
        SquareUnion: "\u2294",
        squarf: "\u25AA",
        squf: "\u25AA",
        srarr: "\u2192",
        Sscr: "\u{1D4AE}",
        sscr: "\u{1D4C8}",
        ssetmn: "\u2216",
        ssmile: "\u2323",
        sstarf: "\u22C6",
        Star: "\u22C6",
        star: "\u2606",
        starf: "\u2605",
        straightepsilon: "\u03F5",
        straightphi: "\u03D5",
        strns: "\xAF",
        Sub: "\u22D0",
        sub: "\u2282",
        subdot: "\u2ABD",
        subE: "\u2AC5",
        sube: "\u2286",
        subedot: "\u2AC3",
        submult: "\u2AC1",
        subnE: "\u2ACB",
        subne: "\u228A",
        subplus: "\u2ABF",
        subrarr: "\u2979",
        Subset: "\u22D0",
        subset: "\u2282",
        subseteq: "\u2286",
        subseteqq: "\u2AC5",
        SubsetEqual: "\u2286",
        subsetneq: "\u228A",
        subsetneqq: "\u2ACB",
        subsim: "\u2AC7",
        subsub: "\u2AD5",
        subsup: "\u2AD3",
        succ: "\u227B",
        succapprox: "\u2AB8",
        succcurlyeq: "\u227D",
        Succeeds: "\u227B",
        SucceedsEqual: "\u2AB0",
        SucceedsSlantEqual: "\u227D",
        SucceedsTilde: "\u227F",
        succeq: "\u2AB0",
        succnapprox: "\u2ABA",
        succneqq: "\u2AB6",
        succnsim: "\u22E9",
        succsim: "\u227F",
        SuchThat: "\u220B",
        Sum: "\u2211",
        sum: "\u2211",
        sung: "\u266A",
        Sup: "\u22D1",
        sup: "\u2283",
        sup1: "\xB9",
        sup2: "\xB2",
        sup3: "\xB3",
        supdot: "\u2ABE",
        supdsub: "\u2AD8",
        supE: "\u2AC6",
        supe: "\u2287",
        supedot: "\u2AC4",
        Superset: "\u2283",
        SupersetEqual: "\u2287",
        suphsol: "\u27C9",
        suphsub: "\u2AD7",
        suplarr: "\u297B",
        supmult: "\u2AC2",
        supnE: "\u2ACC",
        supne: "\u228B",
        supplus: "\u2AC0",
        Supset: "\u22D1",
        supset: "\u2283",
        supseteq: "\u2287",
        supseteqq: "\u2AC6",
        supsetneq: "\u228B",
        supsetneqq: "\u2ACC",
        supsim: "\u2AC8",
        supsub: "\u2AD4",
        supsup: "\u2AD6",
        swarhk: "\u2926",
        swArr: "\u21D9",
        swarr: "\u2199",
        swarrow: "\u2199",
        swnwar: "\u292A",
        szlig: "\xDF",
        Tab: "	",
        target: "\u2316",
        Tau: "\u03A4",
        tau: "\u03C4",
        tbrk: "\u23B4",
        Tcaron: "\u0164",
        tcaron: "\u0165",
        Tcedil: "\u0162",
        tcedil: "\u0163",
        Tcy: "\u0422",
        tcy: "\u0442",
        tdot: "\u20DB",
        telrec: "\u2315",
        Tfr: "\u{1D517}",
        tfr: "\u{1D531}",
        there4: "\u2234",
        Therefore: "\u2234",
        therefore: "\u2234",
        Theta: "\u0398",
        theta: "\u03B8",
        thetasym: "\u03D1",
        thetav: "\u03D1",
        thickapprox: "\u2248",
        thicksim: "\u223C",
        ThickSpace: "\u205F\u200A",
        thinsp: "\u2009",
        ThinSpace: "\u2009",
        thkap: "\u2248",
        thksim: "\u223C",
        THORN: "\xDE",
        thorn: "\xFE",
        Tilde: "\u223C",
        tilde: "\u02DC",
        TildeEqual: "\u2243",
        TildeFullEqual: "\u2245",
        TildeTilde: "\u2248",
        times: "\xD7",
        timesb: "\u22A0",
        timesbar: "\u2A31",
        timesd: "\u2A30",
        tint: "\u222D",
        toea: "\u2928",
        top: "\u22A4",
        topbot: "\u2336",
        topcir: "\u2AF1",
        Topf: "\u{1D54B}",
        topf: "\u{1D565}",
        topfork: "\u2ADA",
        tosa: "\u2929",
        tprime: "\u2034",
        TRADE: "\u2122",
        trade: "\u2122",
        triangle: "\u25B5",
        triangledown: "\u25BF",
        triangleleft: "\u25C3",
        trianglelefteq: "\u22B4",
        triangleq: "\u225C",
        triangleright: "\u25B9",
        trianglerighteq: "\u22B5",
        tridot: "\u25EC",
        trie: "\u225C",
        triminus: "\u2A3A",
        TripleDot: "\u20DB",
        triplus: "\u2A39",
        trisb: "\u29CD",
        tritime: "\u2A3B",
        trpezium: "\u23E2",
        Tscr: "\u{1D4AF}",
        tscr: "\u{1D4C9}",
        TScy: "\u0426",
        tscy: "\u0446",
        TSHcy: "\u040B",
        tshcy: "\u045B",
        Tstrok: "\u0166",
        tstrok: "\u0167",
        twixt: "\u226C",
        twoheadleftarrow: "\u219E",
        twoheadrightarrow: "\u21A0",
        Uacute: "\xDA",
        uacute: "\xFA",
        Uarr: "\u219F",
        uArr: "\u21D1",
        uarr: "\u2191",
        Uarrocir: "\u2949",
        Ubrcy: "\u040E",
        ubrcy: "\u045E",
        Ubreve: "\u016C",
        ubreve: "\u016D",
        Ucirc: "\xDB",
        ucirc: "\xFB",
        Ucy: "\u0423",
        ucy: "\u0443",
        udarr: "\u21C5",
        Udblac: "\u0170",
        udblac: "\u0171",
        udhar: "\u296E",
        ufisht: "\u297E",
        Ufr: "\u{1D518}",
        ufr: "\u{1D532}",
        Ugrave: "\xD9",
        ugrave: "\xF9",
        uHar: "\u2963",
        uharl: "\u21BF",
        uharr: "\u21BE",
        uhblk: "\u2580",
        ulcorn: "\u231C",
        ulcorner: "\u231C",
        ulcrop: "\u230F",
        ultri: "\u25F8",
        Umacr: "\u016A",
        umacr: "\u016B",
        uml: "\xA8",
        UnderBar: "_",
        UnderBrace: "\u23DF",
        UnderBracket: "\u23B5",
        UnderParenthesis: "\u23DD",
        Union: "\u22C3",
        UnionPlus: "\u228E",
        Uogon: "\u0172",
        uogon: "\u0173",
        Uopf: "\u{1D54C}",
        uopf: "\u{1D566}",
        UpArrow: "\u2191",
        Uparrow: "\u21D1",
        uparrow: "\u2191",
        UpArrowBar: "\u2912",
        UpArrowDownArrow: "\u21C5",
        UpDownArrow: "\u2195",
        Updownarrow: "\u21D5",
        updownarrow: "\u2195",
        UpEquilibrium: "\u296E",
        upharpoonleft: "\u21BF",
        upharpoonright: "\u21BE",
        uplus: "\u228E",
        UpperLeftArrow: "\u2196",
        UpperRightArrow: "\u2197",
        Upsi: "\u03D2",
        upsi: "\u03C5",
        upsih: "\u03D2",
        Upsilon: "\u03A5",
        upsilon: "\u03C5",
        UpTee: "\u22A5",
        UpTeeArrow: "\u21A5",
        upuparrows: "\u21C8",
        urcorn: "\u231D",
        urcorner: "\u231D",
        urcrop: "\u230E",
        Uring: "\u016E",
        uring: "\u016F",
        urtri: "\u25F9",
        Uscr: "\u{1D4B0}",
        uscr: "\u{1D4CA}",
        utdot: "\u22F0",
        Utilde: "\u0168",
        utilde: "\u0169",
        utri: "\u25B5",
        utrif: "\u25B4",
        uuarr: "\u21C8",
        Uuml: "\xDC",
        uuml: "\xFC",
        uwangle: "\u29A7",
        vangrt: "\u299C",
        varepsilon: "\u03F5",
        varkappa: "\u03F0",
        varnothing: "\u2205",
        varphi: "\u03D5",
        varpi: "\u03D6",
        varpropto: "\u221D",
        vArr: "\u21D5",
        varr: "\u2195",
        varrho: "\u03F1",
        varsigma: "\u03C2",
        varsubsetneq: "\u228A\uFE00",
        varsubsetneqq: "\u2ACB\uFE00",
        varsupsetneq: "\u228B\uFE00",
        varsupsetneqq: "\u2ACC\uFE00",
        vartheta: "\u03D1",
        vartriangleleft: "\u22B2",
        vartriangleright: "\u22B3",
        Vbar: "\u2AEB",
        vBar: "\u2AE8",
        vBarv: "\u2AE9",
        Vcy: "\u0412",
        vcy: "\u0432",
        VDash: "\u22AB",
        Vdash: "\u22A9",
        vDash: "\u22A8",
        vdash: "\u22A2",
        Vdashl: "\u2AE6",
        Vee: "\u22C1",
        vee: "\u2228",
        veebar: "\u22BB",
        veeeq: "\u225A",
        vellip: "\u22EE",
        Verbar: "\u2016",
        verbar: "|",
        Vert: "\u2016",
        vert: "|",
        VerticalBar: "\u2223",
        VerticalLine: "|",
        VerticalSeparator: "\u2758",
        VerticalTilde: "\u2240",
        VeryThinSpace: "\u200A",
        Vfr: "\u{1D519}",
        vfr: "\u{1D533}",
        vltri: "\u22B2",
        vnsub: "\u2282\u20D2",
        vnsup: "\u2283\u20D2",
        Vopf: "\u{1D54D}",
        vopf: "\u{1D567}",
        vprop: "\u221D",
        vrtri: "\u22B3",
        Vscr: "\u{1D4B1}",
        vscr: "\u{1D4CB}",
        vsubnE: "\u2ACB\uFE00",
        vsubne: "\u228A\uFE00",
        vsupnE: "\u2ACC\uFE00",
        vsupne: "\u228B\uFE00",
        Vvdash: "\u22AA",
        vzigzag: "\u299A",
        Wcirc: "\u0174",
        wcirc: "\u0175",
        wedbar: "\u2A5F",
        Wedge: "\u22C0",
        wedge: "\u2227",
        wedgeq: "\u2259",
        weierp: "\u2118",
        Wfr: "\u{1D51A}",
        wfr: "\u{1D534}",
        Wopf: "\u{1D54E}",
        wopf: "\u{1D568}",
        wp: "\u2118",
        wr: "\u2240",
        wreath: "\u2240",
        Wscr: "\u{1D4B2}",
        wscr: "\u{1D4CC}",
        xcap: "\u22C2",
        xcirc: "\u25EF",
        xcup: "\u22C3",
        xdtri: "\u25BD",
        Xfr: "\u{1D51B}",
        xfr: "\u{1D535}",
        xhArr: "\u27FA",
        xharr: "\u27F7",
        Xi: "\u039E",
        xi: "\u03BE",
        xlArr: "\u27F8",
        xlarr: "\u27F5",
        xmap: "\u27FC",
        xnis: "\u22FB",
        xodot: "\u2A00",
        Xopf: "\u{1D54F}",
        xopf: "\u{1D569}",
        xoplus: "\u2A01",
        xotime: "\u2A02",
        xrArr: "\u27F9",
        xrarr: "\u27F6",
        Xscr: "\u{1D4B3}",
        xscr: "\u{1D4CD}",
        xsqcup: "\u2A06",
        xuplus: "\u2A04",
        xutri: "\u25B3",
        xvee: "\u22C1",
        xwedge: "\u22C0",
        Yacute: "\xDD",
        yacute: "\xFD",
        YAcy: "\u042F",
        yacy: "\u044F",
        Ycirc: "\u0176",
        ycirc: "\u0177",
        Ycy: "\u042B",
        ycy: "\u044B",
        yen: "\xA5",
        Yfr: "\u{1D51C}",
        yfr: "\u{1D536}",
        YIcy: "\u0407",
        yicy: "\u0457",
        Yopf: "\u{1D550}",
        yopf: "\u{1D56A}",
        Yscr: "\u{1D4B4}",
        yscr: "\u{1D4CE}",
        YUcy: "\u042E",
        yucy: "\u044E",
        Yuml: "\u0178",
        yuml: "\xFF",
        Zacute: "\u0179",
        zacute: "\u017A",
        Zcaron: "\u017D",
        zcaron: "\u017E",
        Zcy: "\u0417",
        zcy: "\u0437",
        Zdot: "\u017B",
        zdot: "\u017C",
        zeetrf: "\u2128",
        ZeroWidthSpace: "\u200B",
        Zeta: "\u0396",
        zeta: "\u03B6",
        Zfr: "\u2128",
        zfr: "\u{1D537}",
        ZHcy: "\u0416",
        zhcy: "\u0436",
        zigrarr: "\u21DD",
        Zopf: "\u2124",
        zopf: "\u{1D56B}",
        Zscr: "\u{1D4B5}",
        zscr: "\u{1D4CF}",
        zwj: "\u200D",
        zwnj: "\u200C"
      });
      exports.entityMap = exports.HTML_ENTITIES;
    }
  });

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/sax.js
  var require_sax = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/sax.js"(exports) {
      var NAMESPACE = require_conventions().NAMESPACE;
      var nameStartChar = /[A-Z_a-z\xC0-\xD6\xD8-\xF6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]/;
      var nameChar = new RegExp("[\\-\\.0-9" + nameStartChar.source.slice(1, -1) + "\\u00B7\\u0300-\\u036F\\u203F-\\u2040]");
      var tagNamePattern = new RegExp("^" + nameStartChar.source + nameChar.source + "*(?::" + nameStartChar.source + nameChar.source + "*)?$");
      var S_TAG = 0;
      var S_ATTR = 1;
      var S_ATTR_SPACE = 2;
      var S_EQ = 3;
      var S_ATTR_NOQUOT_VALUE = 4;
      var S_ATTR_END = 5;
      var S_TAG_SPACE = 6;
      var S_TAG_CLOSE = 7;
      function ParseError(message, locator) {
        this.message = message;
        this.locator = locator;
        if (Error.captureStackTrace) Error.captureStackTrace(this, ParseError);
      }
      ParseError.prototype = new Error();
      ParseError.prototype.name = ParseError.name;
      function XMLReader() {
      }
      XMLReader.prototype = {
        parse: function(source, defaultNSMap, entityMap) {
          var domBuilder = this.domBuilder;
          domBuilder.startDocument();
          _copy(defaultNSMap, defaultNSMap = {});
          parse(
            source,
            defaultNSMap,
            entityMap,
            domBuilder,
            this.errorHandler
          );
          domBuilder.endDocument();
        }
      };
      function parse(source, defaultNSMapCopy, entityMap, domBuilder, errorHandler) {
        function fixedFromCharCode(code) {
          if (code > 65535) {
            code -= 65536;
            var surrogate1 = 55296 + (code >> 10), surrogate2 = 56320 + (code & 1023);
            return String.fromCharCode(surrogate1, surrogate2);
          } else {
            return String.fromCharCode(code);
          }
        }
        function entityReplacer(a2) {
          var k = a2.slice(1, -1);
          if (Object.hasOwnProperty.call(entityMap, k)) {
            return entityMap[k];
          } else if (k.charAt(0) === "#") {
            return fixedFromCharCode(parseInt(k.substr(1).replace("x", "0x")));
          } else {
            errorHandler.error("entity not found:" + a2);
            return a2;
          }
        }
        function appendText(end2) {
          if (end2 > start) {
            var xt = source.substring(start, end2).replace(/&#?\w+;/g, entityReplacer);
            locator && position(start);
            domBuilder.characters(xt, 0, end2 - start);
            start = end2;
          }
        }
        function position(p, m) {
          while (p >= lineEnd && (m = linePattern.exec(source))) {
            lineStart = m.index;
            lineEnd = lineStart + m[0].length;
            locator.lineNumber++;
          }
          locator.columnNumber = p - lineStart + 1;
        }
        var lineStart = 0;
        var lineEnd = 0;
        var linePattern = /.*(?:\r\n?|\n)|.*$/g;
        var locator = domBuilder.locator;
        var parseStack = [{ currentNSMap: defaultNSMapCopy }];
        var closeMap = {};
        var start = 0;
        while (true) {
          try {
            var tagStart = source.indexOf("<", start);
            if (tagStart < 0) {
              if (!source.substr(start).match(/^\s*$/)) {
                var doc = domBuilder.doc;
                var text = doc.createTextNode(source.substr(start));
                doc.appendChild(text);
                domBuilder.currentElement = text;
              }
              return;
            }
            if (tagStart > start) {
              appendText(tagStart);
            }
            switch (source.charAt(tagStart + 1)) {
              case "/":
                var end = source.indexOf(">", tagStart + 3);
                var tagName = source.substring(tagStart + 2, end).replace(/[ \t\n\r]+$/g, "");
                var config = parseStack.pop();
                if (end < 0) {
                  tagName = source.substring(tagStart + 2).replace(/[\s<].*/, "");
                  errorHandler.error("end tag name: " + tagName + " is not complete:" + config.tagName);
                  end = tagStart + 1 + tagName.length;
                } else if (tagName.match(/\s</)) {
                  tagName = tagName.replace(/[\s<].*/, "");
                  errorHandler.error("end tag name: " + tagName + " maybe not complete");
                  end = tagStart + 1 + tagName.length;
                }
                var localNSMap = config.localNSMap;
                var endMatch = config.tagName == tagName;
                var endIgnoreCaseMach = endMatch || config.tagName && config.tagName.toLowerCase() == tagName.toLowerCase();
                if (endIgnoreCaseMach) {
                  domBuilder.endElement(config.uri, config.localName, tagName);
                  if (localNSMap) {
                    for (var prefix in localNSMap) {
                      if (Object.prototype.hasOwnProperty.call(localNSMap, prefix)) {
                        domBuilder.endPrefixMapping(prefix);
                      }
                    }
                  }
                  if (!endMatch) {
                    errorHandler.fatalError("end tag name: " + tagName + " is not match the current start tagName:" + config.tagName);
                  }
                } else {
                  parseStack.push(config);
                }
                end++;
                break;
              // end elment
              case "?":
                locator && position(tagStart);
                end = parseInstruction(source, tagStart, domBuilder);
                break;
              case "!":
                locator && position(tagStart);
                end = parseDCC(source, tagStart, domBuilder, errorHandler);
                break;
              default:
                locator && position(tagStart);
                var el = new ElementAttributes();
                var currentNSMap = parseStack[parseStack.length - 1].currentNSMap;
                var end = parseElementStartPart(source, tagStart, el, currentNSMap, entityReplacer, errorHandler);
                var len = el.length;
                if (!el.closed && fixSelfClosed(source, end, el.tagName, closeMap)) {
                  el.closed = true;
                  if (!entityMap.nbsp) {
                    errorHandler.warning("unclosed xml attribute");
                  }
                }
                if (locator && len) {
                  var locator2 = copyLocator(locator, {});
                  for (var i = 0; i < len; i++) {
                    var a = el[i];
                    position(a.offset);
                    a.locator = copyLocator(locator, {});
                  }
                  domBuilder.locator = locator2;
                  if (appendElement(el, domBuilder, currentNSMap)) {
                    parseStack.push(el);
                  }
                  domBuilder.locator = locator;
                } else {
                  if (appendElement(el, domBuilder, currentNSMap)) {
                    parseStack.push(el);
                  }
                }
                if (NAMESPACE.isHTML(el.uri) && !el.closed) {
                  end = parseHtmlSpecialContent(source, end, el.tagName, entityReplacer, domBuilder);
                } else {
                  end++;
                }
            }
          } catch (e) {
            if (e instanceof ParseError) {
              throw e;
            }
            errorHandler.error("element parse error: " + e);
            end = -1;
          }
          if (end > start) {
            start = end;
          } else {
            appendText(Math.max(tagStart, start) + 1);
          }
        }
      }
      function copyLocator(f, t) {
        t.lineNumber = f.lineNumber;
        t.columnNumber = f.columnNumber;
        return t;
      }
      function parseElementStartPart(source, start, el, currentNSMap, entityReplacer, errorHandler) {
        function addAttribute(qname, value2, startIndex) {
          if (el.attributeNames.hasOwnProperty(qname)) {
            errorHandler.fatalError("Attribute " + qname + " redefined");
          }
          el.addValue(
            qname,
            // @see https://www.w3.org/TR/xml/#AVNormalize
            // since the xmldom sax parser does not "interpret" DTD the following is not implemented:
            // - recursive replacement of (DTD) entity references
            // - trimming and collapsing multiple spaces into a single one for attributes that are not of type CDATA
            value2.replace(/[\t\n\r]/g, " ").replace(/&#?\w+;/g, entityReplacer),
            startIndex
          );
        }
        var attrName;
        var value;
        var p = ++start;
        var s = S_TAG;
        while (true) {
          var c = source.charAt(p);
          switch (c) {
            case "=":
              if (s === S_ATTR) {
                attrName = source.slice(start, p);
                s = S_EQ;
              } else if (s === S_ATTR_SPACE) {
                s = S_EQ;
              } else {
                throw new Error("attribute equal must after attrName");
              }
              break;
            case "'":
            case '"':
              if (s === S_EQ || s === S_ATTR) {
                if (s === S_ATTR) {
                  errorHandler.warning('attribute value must after "="');
                  attrName = source.slice(start, p);
                }
                start = p + 1;
                p = source.indexOf(c, start);
                if (p > 0) {
                  value = source.slice(start, p);
                  addAttribute(attrName, value, start - 1);
                  s = S_ATTR_END;
                } else {
                  throw new Error("attribute value no end '" + c + "' match");
                }
              } else if (s == S_ATTR_NOQUOT_VALUE) {
                value = source.slice(start, p);
                addAttribute(attrName, value, start);
                errorHandler.warning('attribute "' + attrName + '" missed start quot(' + c + ")!!");
                start = p + 1;
                s = S_ATTR_END;
              } else {
                throw new Error('attribute value must after "="');
              }
              break;
            case "/":
              switch (s) {
                case S_TAG:
                  el.setTagName(source.slice(start, p));
                case S_ATTR_END:
                case S_TAG_SPACE:
                case S_TAG_CLOSE:
                  s = S_TAG_CLOSE;
                  el.closed = true;
                case S_ATTR_NOQUOT_VALUE:
                case S_ATTR:
                  break;
                case S_ATTR_SPACE:
                  el.closed = true;
                  break;
                //case S_EQ:
                default:
                  throw new Error("attribute invalid close char('/')");
              }
              break;
            case "":
              errorHandler.error("unexpected end of input");
              if (s == S_TAG) {
                el.setTagName(source.slice(start, p));
              }
              return p;
            case ">":
              switch (s) {
                case S_TAG:
                  el.setTagName(source.slice(start, p));
                case S_ATTR_END:
                case S_TAG_SPACE:
                case S_TAG_CLOSE:
                  break;
                //normal
                case S_ATTR_NOQUOT_VALUE:
                //Compatible state
                case S_ATTR:
                  value = source.slice(start, p);
                  if (value.slice(-1) === "/") {
                    el.closed = true;
                    value = value.slice(0, -1);
                  }
                case S_ATTR_SPACE:
                  if (s === S_ATTR_SPACE) {
                    value = attrName;
                  }
                  if (s == S_ATTR_NOQUOT_VALUE) {
                    errorHandler.warning('attribute "' + value + '" missed quot(")!');
                    addAttribute(attrName, value, start);
                  } else {
                    if (!NAMESPACE.isHTML(currentNSMap[""]) || !value.match(/^(?:disabled|checked|selected)$/i)) {
                      errorHandler.warning('attribute "' + value + '" missed value!! "' + value + '" instead!!');
                    }
                    addAttribute(value, value, start);
                  }
                  break;
                case S_EQ:
                  throw new Error("attribute value missed!!");
              }
              return p;
            /*xml space '\x20' | #x9 | #xD | #xA; */
            case "\x80":
              c = " ";
            default:
              if (c <= " ") {
                switch (s) {
                  case S_TAG:
                    el.setTagName(source.slice(start, p));
                    s = S_TAG_SPACE;
                    break;
                  case S_ATTR:
                    attrName = source.slice(start, p);
                    s = S_ATTR_SPACE;
                    break;
                  case S_ATTR_NOQUOT_VALUE:
                    var value = source.slice(start, p);
                    errorHandler.warning('attribute "' + value + '" missed quot(")!!');
                    addAttribute(attrName, value, start);
                  case S_ATTR_END:
                    s = S_TAG_SPACE;
                    break;
                }
              } else {
                switch (s) {
                  //case S_TAG:void();break;
                  //case S_ATTR:void();break;
                  //case S_ATTR_NOQUOT_VALUE:void();break;
                  case S_ATTR_SPACE:
                    var tagName = el.tagName;
                    if (!NAMESPACE.isHTML(currentNSMap[""]) || !attrName.match(/^(?:disabled|checked|selected)$/i)) {
                      errorHandler.warning('attribute "' + attrName + '" missed value!! "' + attrName + '" instead2!!');
                    }
                    addAttribute(attrName, attrName, start);
                    start = p;
                    s = S_ATTR;
                    break;
                  case S_ATTR_END:
                    errorHandler.warning('attribute space is required"' + attrName + '"!!');
                  case S_TAG_SPACE:
                    s = S_ATTR;
                    start = p;
                    break;
                  case S_EQ:
                    s = S_ATTR_NOQUOT_VALUE;
                    start = p;
                    break;
                  case S_TAG_CLOSE:
                    throw new Error("elements closed character '/' and '>' must be connected to");
                }
              }
          }
          p++;
        }
      }
      function appendElement(el, domBuilder, currentNSMap) {
        var tagName = el.tagName;
        var localNSMap = null;
        var i = el.length;
        while (i--) {
          var a = el[i];
          var qName = a.qName;
          var value = a.value;
          var nsp = qName.indexOf(":");
          if (nsp > 0) {
            var prefix = a.prefix = qName.slice(0, nsp);
            var localName = qName.slice(nsp + 1);
            var nsPrefix = prefix === "xmlns" && localName;
          } else {
            localName = qName;
            prefix = null;
            nsPrefix = qName === "xmlns" && "";
          }
          a.localName = localName;
          if (nsPrefix !== false) {
            if (localNSMap == null) {
              localNSMap = {};
              _copy(currentNSMap, currentNSMap = {});
            }
            currentNSMap[nsPrefix] = localNSMap[nsPrefix] = value;
            a.uri = NAMESPACE.XMLNS;
            domBuilder.startPrefixMapping(nsPrefix, value);
          }
        }
        var i = el.length;
        while (i--) {
          a = el[i];
          var prefix = a.prefix;
          if (prefix) {
            if (prefix === "xml") {
              a.uri = NAMESPACE.XML;
            }
            if (prefix !== "xmlns") {
              a.uri = currentNSMap[prefix || ""];
            }
          }
        }
        var nsp = tagName.indexOf(":");
        if (nsp > 0) {
          prefix = el.prefix = tagName.slice(0, nsp);
          localName = el.localName = tagName.slice(nsp + 1);
        } else {
          prefix = null;
          localName = el.localName = tagName;
        }
        var ns = el.uri = currentNSMap[prefix || ""];
        domBuilder.startElement(ns, localName, tagName, el);
        if (el.closed) {
          domBuilder.endElement(ns, localName, tagName);
          if (localNSMap) {
            for (prefix in localNSMap) {
              if (Object.prototype.hasOwnProperty.call(localNSMap, prefix)) {
                domBuilder.endPrefixMapping(prefix);
              }
            }
          }
        } else {
          el.currentNSMap = currentNSMap;
          el.localNSMap = localNSMap;
          return true;
        }
      }
      function parseHtmlSpecialContent(source, elStartEnd, tagName, entityReplacer, domBuilder) {
        if (/^(?:script|textarea)$/i.test(tagName)) {
          var elEndStart = source.indexOf("</" + tagName + ">", elStartEnd);
          var text = source.substring(elStartEnd + 1, elEndStart);
          if (/[&<]/.test(text)) {
            if (/^script$/i.test(tagName)) {
              domBuilder.characters(text, 0, text.length);
              return elEndStart;
            }
            text = text.replace(/&#?\w+;/g, entityReplacer);
            domBuilder.characters(text, 0, text.length);
            return elEndStart;
          }
        }
        return elStartEnd + 1;
      }
      function fixSelfClosed(source, elStartEnd, tagName, closeMap) {
        var pos = closeMap[tagName];
        if (pos == null) {
          pos = source.lastIndexOf("</" + tagName + ">");
          if (pos < elStartEnd) {
            pos = source.lastIndexOf("</" + tagName);
          }
          closeMap[tagName] = pos;
        }
        return pos < elStartEnd;
      }
      function _copy(source, target) {
        for (var n in source) {
          if (Object.prototype.hasOwnProperty.call(source, n)) {
            target[n] = source[n];
          }
        }
      }
      function parseDCC(source, start, domBuilder, errorHandler) {
        var next = source.charAt(start + 2);
        switch (next) {
          case "-":
            if (source.charAt(start + 3) === "-") {
              var end = source.indexOf("-->", start + 4);
              if (end > start) {
                domBuilder.comment(source, start + 4, end - start - 4);
                return end + 3;
              } else {
                errorHandler.error("Unclosed comment");
                return -1;
              }
            } else {
              return -1;
            }
          default:
            if (source.substr(start + 3, 6) == "CDATA[") {
              var end = source.indexOf("]]>", start + 9);
              domBuilder.startCDATA();
              domBuilder.characters(source, start + 9, end - start - 9);
              domBuilder.endCDATA();
              return end + 3;
            }
            var matchs = split(source, start);
            var len = matchs.length;
            if (len > 1 && /!doctype/i.test(matchs[0][0])) {
              var name = matchs[1][0];
              var pubid = false;
              var sysid = false;
              if (len > 3) {
                if (/^public$/i.test(matchs[2][0])) {
                  pubid = matchs[3][0];
                  sysid = len > 4 && matchs[4][0];
                } else if (/^system$/i.test(matchs[2][0])) {
                  sysid = matchs[3][0];
                }
              }
              var lastMatch = matchs[len - 1];
              domBuilder.startDTD(name, pubid, sysid);
              domBuilder.endDTD();
              return lastMatch.index + lastMatch[0].length;
            }
        }
        return -1;
      }
      function parseInstruction(source, start, domBuilder) {
        var end = source.indexOf("?>", start);
        if (end) {
          var match = source.substring(start, end).match(/^<\?(\S*)\s*([\s\S]*?)\s*$/);
          if (match) {
            var len = match[0].length;
            domBuilder.processingInstruction(match[1], match[2]);
            return end + 2;
          } else {
            return -1;
          }
        }
        return -1;
      }
      function ElementAttributes() {
        this.attributeNames = {};
      }
      ElementAttributes.prototype = {
        setTagName: function(tagName) {
          if (!tagNamePattern.test(tagName)) {
            throw new Error("invalid tagName:" + tagName);
          }
          this.tagName = tagName;
        },
        addValue: function(qName, value, offset) {
          if (!tagNamePattern.test(qName)) {
            throw new Error("invalid attribute:" + qName);
          }
          this.attributeNames[qName] = this.length;
          this[this.length++] = { qName, value, offset };
        },
        length: 0,
        getLocalName: function(i) {
          return this[i].localName;
        },
        getLocator: function(i) {
          return this[i].locator;
        },
        getQName: function(i) {
          return this[i].qName;
        },
        getURI: function(i) {
          return this[i].uri;
        },
        getValue: function(i) {
          return this[i].value;
        }
        //	,getIndex:function(uri, localName)){
        //		if(localName){
        //
        //		}else{
        //			var qName = uri
        //		}
        //	},
        //	getValue:function(){return this.getValue(this.getIndex.apply(this,arguments))},
        //	getType:function(uri,localName){}
        //	getType:function(i){},
      };
      function split(source, start) {
        var match;
        var buf = [];
        var reg = /'[^']+'|"[^"]+"|[^\s<>\/=]+=?|(\/?\s*>|<)/g;
        reg.lastIndex = start;
        reg.exec(source);
        while (match = reg.exec(source)) {
          buf.push(match);
          if (match[1]) return buf;
        }
      }
      exports.XMLReader = XMLReader;
      exports.ParseError = ParseError;
    }
  });

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/dom-parser.js
  var require_dom_parser = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/dom-parser.js"(exports) {
      var conventions = require_conventions();
      var dom = require_dom();
      var entities = require_entities();
      var sax = require_sax();
      var DOMImplementation = dom.DOMImplementation;
      var NAMESPACE = conventions.NAMESPACE;
      var ParseError = sax.ParseError;
      var XMLReader = sax.XMLReader;
      function normalizeLineEndings(input) {
        return input.replace(/\r[\n\u0085]/g, "\n").replace(/[\r\u0085\u2028]/g, "\n");
      }
      function DOMParser3(options) {
        this.options = options || { locator: {} };
      }
      DOMParser3.prototype.parseFromString = function(source, mimeType) {
        var options = this.options;
        var sax2 = new XMLReader();
        var domBuilder = options.domBuilder || new DOMHandler();
        var errorHandler = options.errorHandler;
        var locator = options.locator;
        var defaultNSMap = options.xmlns || {};
        var isHTML = /\/x?html?$/.test(mimeType);
        var entityMap = isHTML ? entities.HTML_ENTITIES : entities.XML_ENTITIES;
        if (locator) {
          domBuilder.setDocumentLocator(locator);
        }
        sax2.errorHandler = buildErrorHandler(errorHandler, domBuilder, locator);
        sax2.domBuilder = options.domBuilder || domBuilder;
        if (isHTML) {
          defaultNSMap[""] = NAMESPACE.HTML;
        }
        defaultNSMap.xml = defaultNSMap.xml || NAMESPACE.XML;
        var normalize = options.normalizeLineEndings || normalizeLineEndings;
        if (source && typeof source === "string") {
          sax2.parse(
            normalize(source),
            defaultNSMap,
            entityMap
          );
        } else {
          sax2.errorHandler.error("invalid doc source");
        }
        return domBuilder.doc;
      };
      function buildErrorHandler(errorImpl, domBuilder, locator) {
        if (!errorImpl) {
          if (domBuilder instanceof DOMHandler) {
            return domBuilder;
          }
          errorImpl = domBuilder;
        }
        var errorHandler = {};
        var isCallback = errorImpl instanceof Function;
        locator = locator || {};
        function build(key) {
          var fn = errorImpl[key];
          if (!fn && isCallback) {
            fn = errorImpl.length == 2 ? function(msg) {
              errorImpl(key, msg);
            } : errorImpl;
          }
          errorHandler[key] = fn && function(msg) {
            fn("[xmldom " + key + "]	" + msg + _locator(locator));
          } || function() {
          };
        }
        build("warning");
        build("error");
        build("fatalError");
        return errorHandler;
      }
      function DOMHandler() {
        this.cdata = false;
      }
      function position(locator, node) {
        node.lineNumber = locator.lineNumber;
        node.columnNumber = locator.columnNumber;
      }
      DOMHandler.prototype = {
        startDocument: function() {
          this.doc = new DOMImplementation().createDocument(null, null, null);
          if (this.locator) {
            this.doc.documentURI = this.locator.systemId;
          }
        },
        startElement: function(namespaceURI, localName, qName, attrs) {
          var doc = this.doc;
          var el = doc.createElementNS(namespaceURI, qName || localName);
          var len = attrs.length;
          appendElement(this, el);
          this.currentElement = el;
          this.locator && position(this.locator, el);
          for (var i = 0; i < len; i++) {
            var namespaceURI = attrs.getURI(i);
            var value = attrs.getValue(i);
            var qName = attrs.getQName(i);
            var attr = doc.createAttributeNS(namespaceURI, qName);
            this.locator && position(attrs.getLocator(i), attr);
            attr.value = attr.nodeValue = value;
            el.setAttributeNode(attr);
          }
        },
        endElement: function(namespaceURI, localName, qName) {
          var current = this.currentElement;
          var tagName = current.tagName;
          this.currentElement = current.parentNode;
        },
        startPrefixMapping: function(prefix, uri) {
        },
        endPrefixMapping: function(prefix) {
        },
        processingInstruction: function(target, data) {
          var ins = this.doc.createProcessingInstruction(target, data);
          this.locator && position(this.locator, ins);
          appendElement(this, ins);
        },
        ignorableWhitespace: function(ch, start, length) {
        },
        characters: function(chars, start, length) {
          chars = _toString.apply(this, arguments);
          if (chars) {
            if (this.cdata) {
              var charNode = this.doc.createCDATASection(chars);
            } else {
              var charNode = this.doc.createTextNode(chars);
            }
            if (this.currentElement) {
              this.currentElement.appendChild(charNode);
            } else if (/^\s*$/.test(chars)) {
              this.doc.appendChild(charNode);
            }
            this.locator && position(this.locator, charNode);
          }
        },
        skippedEntity: function(name) {
        },
        endDocument: function() {
          this.doc.normalize();
        },
        setDocumentLocator: function(locator) {
          if (this.locator = locator) {
            locator.lineNumber = 0;
          }
        },
        //LexicalHandler
        comment: function(chars, start, length) {
          chars = _toString.apply(this, arguments);
          var comm = this.doc.createComment(chars);
          this.locator && position(this.locator, comm);
          appendElement(this, comm);
        },
        startCDATA: function() {
          this.cdata = true;
        },
        endCDATA: function() {
          this.cdata = false;
        },
        startDTD: function(name, publicId, systemId) {
          var impl = this.doc.implementation;
          if (impl && impl.createDocumentType) {
            var dt = impl.createDocumentType(name, publicId, systemId);
            this.locator && position(this.locator, dt);
            appendElement(this, dt);
            this.doc.doctype = dt;
          }
        },
        /**
         * @see org.xml.sax.ErrorHandler
         * @link http://www.saxproject.org/apidoc/org/xml/sax/ErrorHandler.html
         */
        warning: function(error) {
          console.warn("[xmldom warning]	" + error, _locator(this.locator));
        },
        error: function(error) {
          console.error("[xmldom error]	" + error, _locator(this.locator));
        },
        fatalError: function(error) {
          throw new ParseError(error, this.locator);
        }
      };
      function _locator(l) {
        if (l) {
          return "\n@" + (l.systemId || "") + "#[line:" + l.lineNumber + ",col:" + l.columnNumber + "]";
        }
      }
      function _toString(chars, start, length) {
        if (typeof chars == "string") {
          return chars.substr(start, length);
        } else {
          if (chars.length >= start + length || start) {
            return new java.lang.String(chars, start, length) + "";
          }
          return chars;
        }
      }
      "endDTD,startEntity,endEntity,attributeDecl,elementDecl,externalEntityDecl,internalEntityDecl,resolveEntity,getExternalSubset,notationDecl,unparsedEntityDecl".replace(/\w+/g, function(key) {
        DOMHandler.prototype[key] = function() {
          return null;
        };
      });
      function appendElement(hander, node) {
        if (!hander.currentElement) {
          hander.doc.appendChild(node);
        } else {
          hander.currentElement.appendChild(node);
        }
      }
      exports.__DOMHandler = DOMHandler;
      exports.normalizeLineEndings = normalizeLineEndings;
      exports.DOMParser = DOMParser3;
    }
  });

  // ../review-current-js/node_modules/@xmldom/xmldom/lib/index.js
  var require_lib = __commonJS({
    "../review-current-js/node_modules/@xmldom/xmldom/lib/index.js"(exports) {
      var dom = require_dom();
      exports.DOMImplementation = dom.DOMImplementation;
      exports.XMLSerializer = dom.XMLSerializer;
      exports.DOMParser = require_dom_parser().DOMParser;
    }
  });

  // src/browser.js
  var browser_exports = {};
  __export(browser_exports, {
    Bag: () => Bag,
    BagCbResolver: () => BagCbResolver,
    BagException: () => BagException,
    BagNode: () => BagNode,
    BagNodeContainer: () => BagNodeContainer,
    BagResolver: () => BagResolver,
    BagSerializationError: () => BagSerializationError,
    OpaqueResolver: () => OpaqueResolver,
    RETRY_POLICIES: () => RETRY_POLICIES,
    StorageResolver: () => StorageResolver,
    TYTX: () => src_exports,
    UrlResolver: () => UrlResolver,
    UuidResolver: () => UuidResolver,
    registerResolver: () => registerResolver,
    version: () => version
  });

  // ../review-current-js/node_modules/genro-tytx/js/src/index.js
  var src_exports = {};
  __export(src_exports, {
    CONTENT_TYPES: () => CONTENT_TYPES,
    __version__: () => __version__,
    createDecimal: () => createDecimal,
    fetchTytx: () => fetchTytx,
    fromTytx: () => fromTytx,
    getDecimalLibrary: () => getDecimalLibrary,
    getRegisteredType: () => getRegisteredType,
    getTransport: () => getTransport,
    isDecimal: () => isDecimal,
    registerClass: () => registerClass,
    registerType: () => registerType,
    setDecimalLibrary: () => setDecimalLibrary,
    toTytx: () => toTytx
  });

  // node-module-shim:module
  function createRequire() {
    return function browserRequire(id) {
      throw new Error("Cannot require '" + id + "' in a browser");
    };
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/msgpack.js
  var import_meta = {};
  var require2 = createRequire(import_meta.url);
  var msgpack = null;
  var HAS_MSGPACK = false;
  try {
    msgpack = require2("@msgpack/msgpack");
    HAS_MSGPACK = true;
  } catch {
    HAS_MSGPACK = false;
  }
  function _checkMsgpack() {
    if (!HAS_MSGPACK) {
      throw new Error(
        "@msgpack/msgpack is required for MessagePack support. Install with: npm install @msgpack/msgpack"
      );
    }
  }
  var _extensionCodec = _buildCodec();
  function _buildCodec() {
    if (!HAS_MSGPACK) {
      return null;
    }
    const enc = new TextEncoder();
    const dec = new TextDecoder();
    const codec = new msgpack.ExtensionCodec();
    codec.register({
      type: -1,
      encode: (v) => {
        if (v instanceof Date) {
          const dt = getDateType(v);
          if (dt === "D" || dt === "H") {
            return null;
          }
        }
        return msgpack.encodeTimestampExtension(v);
      },
      decode: (data) => msgpack.decodeTimestampExtension(data)
    });
    codec.register({
      type: 1,
      encode: (v) => {
        if (isDecimal(v)) {
          return enc.encode(v.toString());
        }
        return null;
      },
      decode: (data) => createDecimal(dec.decode(data))
    });
    codec.register({
      type: 2,
      encode: (v) => {
        if (v instanceof Date && getDateType(v) === "D") {
          const y = v.getUTCFullYear();
          const m = String(v.getUTCMonth() + 1).padStart(2, "0");
          const d = String(v.getUTCDate()).padStart(2, "0");
          return enc.encode(`${y}-${m}-${d}`);
        }
        return null;
      },
      decode: (data) => /* @__PURE__ */ new Date(dec.decode(data) + "T00:00:00.000Z")
    });
    codec.register({
      type: 3,
      encode: (v) => {
        if (v instanceof Date && getDateType(v) === "H") {
          const h = String(v.getUTCHours()).padStart(2, "0");
          const m = String(v.getUTCMinutes()).padStart(2, "0");
          const s = String(v.getUTCSeconds()).padStart(2, "0");
          const ms = String(v.getUTCMilliseconds()).padStart(3, "0");
          return enc.encode(`${h}:${m}:${s}.${ms}`);
        }
        return null;
      },
      decode: (data) => {
        const str = dec.decode(data);
        const dotIdx = str.indexOf(".");
        const timePart = dotIdx >= 0 ? str.substring(0, dotIdx) : str;
        const fracStr = dotIdx >= 0 ? str.substring(dotIdx + 1) : "0";
        const [h, m, s] = timePart.split(":");
        const ms = Math.round(+fracStr.substring(0, 3));
        return new Date(Date.UTC(1970, 0, 1, +h, +m, +s, ms));
      }
    });
    codec.register({
      type: 4,
      encode: (v) => {
        const entry = getCustomTypeEntry(v);
        if (entry !== null) {
          const [suffix, serializer] = entry;
          return enc.encode(`${suffix}:${serializer(v)}`);
        }
        return null;
      },
      decode: (data) => {
        const str = dec.decode(data);
        const idx = str.indexOf(":");
        const suffix = str.slice(0, idx);
        const payload = str.slice(idx + 1);
        const entry = SUFFIX_TO_TYPE[suffix];
        if (entry !== void 0) {
          const [, deserializer] = entry;
          return deserializer(payload);
        }
        return `${payload}::${suffix}`;
      }
    });
    return codec;
  }
  function toMsgpack(value) {
    _checkMsgpack();
    return msgpack.encode(value, { extensionCodec: _extensionCodec });
  }
  function fromMsgpack(data) {
    _checkMsgpack();
    return msgpack.decode(data, { extensionCodec: _extensionCodec });
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/utils.js
  function rawEncode(value, forceSuffix = false) {
    const entry = getTypeEntry(value);
    if (entry === null) {
      return [false, String(value)];
    }
    const [suffix, serializer, jsonNative] = entry;
    if (jsonNative && !forceSuffix) {
      return [false, String(value)];
    }
    return [true, `${serializer(value)}::${suffix}`];
  }
  function rawDecode(s) {
    if (!s.includes("::")) {
      return [false, s];
    }
    const lastIndex = s.lastIndexOf("::");
    const value = s.slice(0, lastIndex);
    const suffix = s.slice(lastIndex + 2);
    const entry = SUFFIX_TO_TYPE[suffix];
    if (entry === void 0) {
      return [false, s];
    }
    const [, decoder] = entry;
    return [true, decoder(value)];
  }
  function walk(data, callback, filtercb) {
    if (data !== null && typeof data === "object" && !Array.isArray(data)) {
      const result = {};
      for (const [k, v] of Object.entries(data)) {
        result[k] = walk(v, callback, filtercb);
      }
      return result;
    }
    if (Array.isArray(data)) {
      return data.map((item) => walk(item, callback, filtercb));
    }
    if (filtercb(data)) {
      return callback(data);
    }
    return data;
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/encode.js
  var import_meta2 = {};
  var require3 = createRequire(import_meta2.url);
  function _preprocessValue(value) {
    const entry = getTypeEntry(value);
    if (entry !== null) {
      const [suffix, serializer, jsonNative] = entry;
      if (!jsonNative) {
        return [`${serializer(value)}::${suffix}`, true];
      }
      return [value, false];
    }
    if (Array.isArray(value)) {
      let hasSpecial = false;
      const result = value.map((item) => {
        const [processed, special] = _preprocessValue(item);
        if (special) hasSpecial = true;
        return processed;
      });
      return [result, hasSpecial];
    }
    if (value !== null && typeof value === "object") {
      let hasSpecial = false;
      const result = {};
      for (const [k, v] of Object.entries(value)) {
        const [processed, special] = _preprocessValue(v);
        if (special) hasSpecial = true;
        result[k] = processed;
      }
      return [result, hasSpecial];
    }
    return [value, false];
  }
  function _toJson(value, forceSuffix = false) {
    const [encoded, result] = rawEncode(value, forceSuffix);
    if (encoded) {
      return result;
    }
    const [processed, hasSpecial] = _preprocessValue(value);
    const jsonResult = JSON.stringify(processed);
    if (hasSpecial) {
      return `${jsonResult}::JS`;
    }
    return jsonResult;
  }
  function _toRawJson(value) {
    return JSON.stringify(value);
  }
  function _toRawMsgpack(value) {
    const { encode } = require3("@msgpack/msgpack");
    return encode(value);
  }
  function toTytx(value, transport = null, { raw = false, qs = false, _forceSuffix = false } = {}) {
    if (qs) {
      return `${toQs(value)}::QS`;
    }
    if (raw) {
      if (transport === null || transport === "json") {
        return _toRawJson(value);
      } else if (transport === "msgpack") {
        return _toRawMsgpack(value);
      } else if (transport === "xml") {
        throw new Error("raw=true is not supported for XML transport");
      } else {
        throw new Error(`Unknown transport: ${transport}`);
      }
    }
    if (transport === null || transport === "json") {
      const result = _toJson(value, _forceSuffix);
      if (transport === "json") {
        return `"${result}"`;
      }
      return result;
    } else if (transport === "xml") {
      const result = toXml(value);
      return `<?xml version="1.0" ?><tytx_root>${result}</tytx_root>`;
    } else if (transport === "msgpack") {
      return toMsgpack(value);
    } else {
      throw new Error(`Unknown transport: ${transport}`);
    }
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/xml.js
  var import_meta3 = {};
  var require4 = createRequire(import_meta3.url);
  var DOMParser2;
  var XMLSerializer;
  if (typeof window !== "undefined" && window.DOMParser) {
    DOMParser2 = window.DOMParser;
    XMLSerializer = window.XMLSerializer;
  } else {
    try {
      const xmldom = require4("@xmldom/xmldom");
      DOMParser2 = xmldom.DOMParser;
      XMLSerializer = xmldom.XMLSerializer;
    } catch {
      DOMParser2 = null;
      XMLSerializer = null;
    }
  }
  function _isXmlElement(item) {
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      return false;
    }
    const keys = Object.keys(item);
    if (keys.length !== 1) {
      return false;
    }
    const itemData = item[keys[0]];
    return itemData !== null && typeof itemData === "object" && "value" in itemData;
  }
  function _serializeElement(doc, tag, data) {
    const element = doc.createElement(tag);
    const attrs = data.attrs || {};
    const value = data.value;
    for (const [attrName, attrValue] of Object.entries(attrs)) {
      element.setAttribute(attrName, toTytx(attrValue, null, { _forceSuffix: true }));
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        if (_isXmlElement(item)) {
          const [itemTag] = Object.keys(item);
          const itemData = item[itemTag];
          const childElement = _serializeElement(doc, itemTag, itemData);
          element.appendChild(childElement);
        } else {
          element.textContent = toTytx(value);
          break;
        }
      }
    } else {
      element.textContent = toTytx(value);
    }
    return element;
  }
  function toXml(value) {
    if (!DOMParser2) {
      throw new Error("XML support requires @xmldom/xmldom package in Node.js");
    }
    if (_isXmlElement(value)) {
      const [rootTag] = Object.keys(value);
      const rootData = value[rootTag];
      const doc = new DOMParser2().parseFromString("<root/>", "text/xml");
      const element = _serializeElement(doc, rootTag, rootData);
      const serializer = new XMLSerializer();
      return serializer.serializeToString(element);
    } else {
      return toTytx(value);
    }
  }
  function fromXmlnode(element) {
    const attrs = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      attrs[attr.name] = fromTytx(attr.value);
    }
    const children = [];
    for (let i = 0; i < element.childNodes.length; i++) {
      const node = element.childNodes[i];
      if (node.nodeType === 1) {
        children.push(node);
      }
    }
    if (children.length > 0) {
      if (children.length === 1) {
        const child = children[0];
        const childData = fromXmlnode(child);
        return { attrs, value: { [child.tagName]: childData } };
      } else {
        const valueList = [];
        for (const child of children) {
          const childData = fromXmlnode(child);
          valueList.push({ [child.tagName]: childData });
        }
        return { attrs, value: valueList };
      }
    }
    return { attrs, value: fromTytx(element.textContent) };
  }
  function fromXml(data) {
    if (!DOMParser2) {
      throw new Error("XML support requires @xmldom/xmldom package in Node.js");
    }
    const parser = new DOMParser2();
    const doc = parser.parseFromString(data, "text/xml");
    let root = doc.documentElement;
    if (root.tagName === "tytx_root") {
      let firstElementChild = null;
      for (let i = 0; i < root.childNodes.length; i++) {
        if (root.childNodes[i].nodeType === 1) {
          firstElementChild = root.childNodes[i];
          break;
        }
      }
      if (!firstElementChild) {
        return fromTytx(root.textContent);
      }
      root = firstElementChild;
    }
    const result = fromXmlnode(root);
    return { [root.tagName]: result };
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/decode.js
  function isString(v) {
    return typeof v === "string";
  }
  function _fromJson(data) {
    const [decoded, value] = rawDecode(data);
    if (decoded) {
      return value;
    }
    let jsonData = data;
    if (jsonData.endsWith("::JS")) {
      jsonData = jsonData.slice(0, -4);
    }
    let parsed;
    try {
      parsed = JSON.parse(jsonData);
    } catch {
      return data;
    }
    return walk(parsed, _decodeItem, isString);
  }
  function _decodeItem(s) {
    if (!s.includes("::")) {
      return s;
    }
    return rawDecode(s)[1];
  }
  function _fromXml(data) {
    const result = fromXml(data);
    if (typeof result === "string") {
      return fromTytx(result);
    }
    return result;
  }
  function _fromMsgpack(data) {
    return fromMsgpack(data);
  }
  function fromTytx(data, transport = null) {
    if (data === null) {
      return null;
    }
    if (transport === null || transport === "json") {
      let jsonData = data;
      if (transport === "json" && data.startsWith('"') && data.endsWith('"')) {
        jsonData = data.slice(1, -1);
      }
      return _fromJson(jsonData);
    } else if (transport === "xml") {
      return _fromXml(data);
    } else if (transport === "msgpack") {
      return _fromMsgpack(data);
    } else {
      throw new Error(`Unknown transport: ${transport}`);
    }
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/qs.js
  function toQs(value) {
    if (Array.isArray(value)) {
      return value.map((item) => String(item)).join("&");
    }
    if (value !== null && typeof value === "object") {
      const parts = [];
      for (const [k, v] of Object.entries(value)) {
        const [encoded, result] = rawEncode(v, true);
        if (encoded) {
          parts.push(`${k}=${result}`);
        } else {
          parts.push(`${k}=${v}`);
        }
      }
      return parts.join("&");
    }
    throw new TypeError(`toQs expects object or array, got ${typeof value}`);
  }
  function fromQs(data) {
    if (!data) {
      return [];
    }
    const parts = data.split("&");
    const hasEq = parts.map((p) => p.includes("="));
    const allWithEq = hasEq.every(Boolean);
    const noneWithEq = !hasEq.some(Boolean);
    if (!allWithEq && !noneWithEq) {
      throw new Error("QS format error: mixed items with and without '='");
    }
    if (noneWithEq) {
      return parts.map((p) => fromTytx(p));
    }
    const result = {};
    for (const part of parts) {
      const eqIndex = part.indexOf("=");
      const key = part.slice(0, eqIndex);
      const value = part.slice(eqIndex + 1);
      result[key] = fromTytx(value);
    }
    return result;
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/registry.js
  var import_meta4 = {};
  var require5 = createRequire(import_meta4.url);
  var DecimalJS = null;
  var BigJS = null;
  try {
    DecimalJS = require5("decimal.js");
  } catch {
  }
  try {
    BigJS = require5("big.js");
  } catch {
  }
  var DecimalClass = DecimalJS || BigJS || Number;
  var decimalLibrary = DecimalJS ? "decimal.js" : BigJS ? "big.js" : "number";
  function setDecimalLibrary(name) {
    if (name === "decimal.js" && DecimalJS) {
      DecimalClass = DecimalJS;
      decimalLibrary = "decimal.js";
    } else if (name === "big.js" && BigJS) {
      DecimalClass = BigJS;
      decimalLibrary = "big.js";
    } else {
      DecimalClass = Number;
      decimalLibrary = "number";
    }
  }
  function getDecimalLibrary() {
    return decimalLibrary;
  }
  function createDecimal(value) {
    return new DecimalClass(value);
  }
  function isDecimal(value) {
    if (decimalLibrary === "number") {
      return false;
    }
    return value instanceof DecimalClass;
  }
  function getDateType(d) {
    const isEpochDate = d.getUTCFullYear() === 1970 && d.getUTCMonth() === 0 && d.getUTCDate() === 1;
    const isMidnight = d.getUTCHours() === 0 && d.getUTCMinutes() === 0 && d.getUTCSeconds() === 0 && d.getUTCMilliseconds() === 0;
    if (isEpochDate && !isMidnight) return "H";
    if (isMidnight && !isEpochDate) return "D";
    return "DHZ";
  }
  function _serializeDecimal(v) {
    return v.toString();
  }
  function _serializeDate(v) {
    const year = v.getUTCFullYear();
    const month = String(v.getUTCMonth() + 1).padStart(2, "0");
    const day = String(v.getUTCDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }
  function _serializeDatetime(v) {
    return v.toISOString();
  }
  function _serializeTime(v) {
    const hours = String(v.getUTCHours()).padStart(2, "0");
    const minutes = String(v.getUTCMinutes()).padStart(2, "0");
    const seconds = String(v.getUTCSeconds()).padStart(2, "0");
    const millis = String(v.getUTCMilliseconds()).padStart(3, "0");
    return `${hours}:${minutes}:${seconds}.${millis}`;
  }
  function _serializeBool(v) {
    return v ? "true" : "false";
  }
  function _serializeInt(v) {
    return v.toString();
  }
  function _serializeFloat(v) {
    return v.toString();
  }
  function _serializeRaw(v) {
    let binary = "";
    for (let i = 0; i < v.length; i += 32768) {
      binary += String.fromCharCode.apply(null, v.subarray(i, i + 32768));
    }
    return btoa(binary);
  }
  var CUSTOM_TYPES = [];
  function getCustomTypeEntry(value) {
    if (value === null || typeof value !== "object") {
      return null;
    }
    for (const [cls, suffix, serializer, jsonNative] of CUSTOM_TYPES) {
      if (value.constructor === cls) {
        return [suffix, serializer, jsonNative];
      }
    }
    return null;
  }
  function getTypeEntry(value) {
    if (value === null) {
      return ["NN", () => "", true];
    }
    if (isDecimal(value)) {
      return ["N", _serializeDecimal, false];
    }
    if (value instanceof Uint8Array) {
      return ["RAW", _serializeRaw, false];
    }
    if (value instanceof Date) {
      const dateType = getDateType(value);
      if (dateType === "D") {
        return ["D", _serializeDate, false];
      } else if (dateType === "H") {
        return ["H", _serializeTime, false];
      } else {
        return ["DHZ", _serializeDatetime, false];
      }
    }
    if (typeof value === "boolean") {
      return ["B", _serializeBool, true];
    }
    if (typeof value === "number") {
      if (Number.isInteger(value)) {
        return ["L", _serializeInt, true];
      } else {
        return ["R", _serializeFloat, true];
      }
    }
    return getCustomTypeEntry(value);
  }
  function _deserializeDecimal(s) {
    return createDecimal(s);
  }
  function _deserializeDate(s) {
    const [year, month, day] = s.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, day, 0, 0, 0, 0));
  }
  function _deserializeDatetime(s) {
    return new Date(s);
  }
  function _deserializeTime(s) {
    const [h, m, rest] = s.split(":");
    const [sec, ms] = rest.split(".");
    return new Date(Date.UTC(1970, 0, 1, Number(h), Number(m), Number(sec), Number(ms || 0)));
  }
  function _deserializeBool(s) {
    return s.toLowerCase() === "true";
  }
  function _deserializeInt(s) {
    return parseInt(s, 10);
  }
  function _deserializeFloat(s) {
    return parseFloat(s);
  }
  function _deserializeStr(s) {
    return s;
  }
  function _deserializeNone(s) {
    return null;
  }
  var BASE64_PATTERN = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
  function _deserializeRaw(s) {
    if (!BASE64_PATTERN.test(s)) {
      throw new Error(`RAW payload is not standard padded base64: '${s}'`);
    }
    const binary = atob(s);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      out[i] = binary.charCodeAt(i);
    }
    return out;
  }
  function _deserializeQs(s) {
    return fromQs(s);
  }
  var SUFFIX_PATTERN = /^[A-Z]+$/;
  var SUFFIX_TO_TYPE = {
    "N": [Object, _deserializeDecimal],
    // Object as placeholder for Decimal type
    "D": [Date, _deserializeDate],
    "DH": [Date, _deserializeDatetime],
    // deprecated, still accepted
    "DHZ": [Date, _deserializeDatetime],
    // canonical
    "H": [Date, _deserializeTime],
    "L": [Number, _deserializeInt],
    "R": [Number, _deserializeFloat],
    "T": [String, _deserializeStr],
    "B": [Boolean, _deserializeBool],
    "QS": [Object, _deserializeQs],
    "NN": [null, _deserializeNone],
    "RAW": [Uint8Array, _deserializeRaw]
  };
  function getRegisteredType(suffix) {
    return Object.hasOwn(SUFFIX_TO_TYPE, suffix) ? SUFFIX_TO_TYPE[suffix][0] : null;
  }
  function registerType(cls, suffix, serializer, deserializer, jsonNative = false) {
    if (typeof suffix !== "string" || !SUFFIX_PATTERN.test(suffix)) {
      throw new Error(
        `TYTX suffix '${suffix}' is invalid: expected uppercase ASCII letters only`
      );
    }
    const existing = SUFFIX_TO_TYPE[suffix];
    if (existing !== void 0 && existing[0] !== cls) {
      const owner = existing[0] === null ? "null" : existing[0].name;
      throw new Error(`TYTX suffix '${suffix}' is already registered for ${owner}`);
    }
    CUSTOM_TYPES = CUSTOM_TYPES.filter(([c]) => c !== cls);
    CUSTOM_TYPES.push([cls, suffix, serializer, jsonNative]);
    SUFFIX_TO_TYPE[suffix] = [cls, deserializer];
  }
  function registerClass(cls) {
    if (!cls.tytxSuffix) {
      throw new Error(`registerClass: ${cls.name} is missing a static tytxSuffix`);
    }
    if (typeof cls.prototype?.toTytx !== "function") {
      throw new Error(`registerClass: ${cls.name} is missing a toTytx method`);
    }
    if (typeof cls.fromTytx !== "function") {
      throw new Error(`registerClass: ${cls.name} is missing a static fromTytx method`);
    }
    registerType(
      cls,
      cls.tytxSuffix,
      (obj) => obj.toTytx(),
      (s) => cls.fromTytx(s),
      cls.tytxJsonNative || false
    );
    return cls;
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/http.js
  var CONTENT_TYPES = {
    json: "application/json",
    xml: "application/xml",
    msgpack: "application/msgpack"
  };
  function getTransport(contentType) {
    if (!contentType) return null;
    const ct = contentType.toLowerCase();
    if (ct.includes("json")) return "json";
    if (ct.includes("xml")) return "xml";
    if (ct.includes("msgpack")) return "msgpack";
    return null;
  }
  async function fetchTytx(url, options = {}) {
    const {
      body,
      transport = "json",
      method = body !== void 0 ? "POST" : "GET",
      headers = {},
      ...fetchOptions
    } = options;
    const requestHeaders = {
      "X-TYTX-Transport": transport,
      ...headers
    };
    let requestBody;
    if (body !== void 0) {
      requestHeaders["Content-Type"] = CONTENT_TYPES[transport];
      const encoded = toTytx(body, transport);
      if (transport === "msgpack") {
        requestBody = encoded;
      } else {
        requestBody = encoded;
      }
    }
    const response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: requestBody,
      ...fetchOptions
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const responseContentType = response.headers.get("Content-Type") || "";
    const responseTransport = getTransport(responseContentType) || transport;
    let responseData;
    if (responseTransport === "msgpack") {
      const buffer = await response.arrayBuffer();
      responseData = fromTytx(Buffer.from(buffer), responseTransport);
    } else {
      const text = await response.text();
      responseData = fromTytx(text, responseTransport);
    }
    return responseData;
  }

  // ../review-current-js/node_modules/genro-tytx/js/src/index.js
  var __version__ = "0.15.0";

  // src/resolver.js
  var RETRY_POLICIES = {
    network: {
      maxAttempts: 3,
      delay: 1,
      backoff: 2,
      jitter: true,
      on: ["TypeError", "NetworkError", "AbortError"]
    },
    aggressive: {
      maxAttempts: 5,
      delay: 0.5,
      backoff: 2,
      jitter: true,
      on: ["Error"]
    },
    gentle: {
      maxAttempts: 2,
      delay: 2,
      backoff: 1.5,
      jitter: false,
      on: ["TypeError", "NetworkError"]
    }
  };
  function getRetryPolicy(resolver) {
    const policy = resolver._retryPolicy;
    if (policy === null || policy === void 0) {
      return null;
    }
    if (typeof policy === "string") {
      return RETRY_POLICIES[policy] || null;
    }
    return policy;
  }
  function shouldRetry(error, errorTypes) {
    return errorTypes.some((type) => {
      if (type === "Error") return true;
      return error.name === type || error.constructor.name === type;
    });
  }
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  async function withRetry(fn, policy) {
    if (!policy) {
      return fn();
    }
    const maxAttempts = policy.maxAttempts || 3;
    const delay = policy.delay || 1;
    const backoff = policy.backoff || 2;
    const jitter = policy.jitter !== false;
    const errorTypes = policy.on || ["Error"];
    let lastError = null;
    let currentDelay = delay * 1e3;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const result = fn();
        if (result instanceof Promise) {
          return await result;
        }
        return result;
      } catch (error) {
        lastError = error;
        if (attempt < maxAttempts - 1 && shouldRetry(error, errorTypes)) {
          let sleepTime = currentDelay;
          if (jitter) {
            sleepTime *= 1 + Math.random() * 0.1;
          }
          await sleep(sleepTime);
          currentDelay *= backoff;
        } else {
          throw error;
        }
      }
    }
    throw lastError;
  }
  var _BagResolver = class _BagResolver {
    /**
     * Create a new resolver.
     *
     * @param {Object} kwargs - Configuration options merged with classKwargs.
     */
    constructor(kwargs = {}) {
      const defaults = this.constructor.classKwargs;
      const merged = { ...defaults, ...kwargs };
      this.cacheTime = merged.cacheTime;
      this._readOnly = merged.readOnly;
      this._asBag = merged.asBag;
      this._retryPolicy = merged.retryPolicy;
      this._kw = {};
      const internalParams = this.constructor.internalParams;
      for (const [key, value] of Object.entries(merged)) {
        if (!internalParams.has(key)) {
          this._kw[key] = value;
        }
      }
      this._lastUpdate = null;
      this._node = null;
      this._lastEffectiveFingerprint = null;
      this._cachedValue = null;
      this.init();
    }
    /**
     * Hook called at the end of constructor.
     * Override in subclasses for custom initialization.
     */
    init() {
    }
    /**
     * Set the parent node (called when resolver is attached to a node).
     *
     * @param {BagNode} node - The node this resolver is attached to.
     */
    setNode(node) {
      if (node !== this._node && !this.readOnly && this._lastUpdate !== null) {
        this.reset();
      }
      this._node = node;
      this.onSetResolver(node);
    }
    /**
     * Hook called when resolver is attached to a node.
     * Override in subclasses for custom initialization.
     *
     * @param {BagNode} node - The node this resolver is attached to.
     */
    onSetResolver(node) {
    }
    /**
     * Get the parent node.
     *
     * @returns {BagNode|null}
     */
    get node() {
      return this._node;
    }
    /**
     * Get cache time setting.
     *
     * @returns {number}
     */
    get cacheTime() {
      return this._cacheTime;
    }
    /**
     * Set cache time.
     *
     * @param {number} value
     */
    set cacheTime(value) {
      if (typeof value === "boolean") {
        throw new TypeError("cacheTime must be numeric; use a negative value for infinite caching");
      }
      this._cacheTime = value;
    }
    /**
     * Check if resolver is read-only (value not stored in node).
     *
     * @returns {boolean}
     */
    get readOnly() {
      return this._readOnly;
    }
    /**
     * Check if cached value has expired.
     *
     * @returns {boolean}
     */
    get expired() {
      if (this._cacheTime < 0) {
        return this._lastUpdate === null;
      }
      if (this._cacheTime === 0) {
        return true;
      }
      if (this._lastUpdate === null) {
        return true;
      }
      const now = Date.now();
      const deltaSeconds = (now - this._lastUpdate) / 1e3;
      return deltaSeconds > this._cacheTime;
    }
    /**
     * Reset the cache, forcing next resolve to call load().
     */
    reset() {
      this._lastUpdate = null;
      this._lastEffectiveFingerprint = null;
    }
    /**
     * Readonly caches live in the resolver; writable caches use the attached node.
     *
     * @returns {*} The cached value.
     */
    get cachedValue() {
      return !this.readOnly && this._node ? this._node._value : this._cachedValue;
    }
    /**
     * Set cached value in parent node or local storage.
     *
     * @param {*} value
     */
    set cachedValue(value) {
      if (!this.readOnly && this._node) {
        this._node.setValue(value, false);
      } else {
        this._cachedValue = value;
      }
    }
    /**
     * Compute fingerprint of effective parameters for cache invalidation.
     *
     * @param {Object} effectiveKw - The effective kwargs.
     * @returns {string} JSON string fingerprint.
     * @private
     */
    _computeEffectiveFingerprint(effectiveKw) {
      return JSON.stringify(Object.entries(effectiveKw).sort());
    }
    /**
     * Resolve the value. Main entry point.
     *
     * @param {Object} options - Resolution options.
     * @param {boolean} options.static - If true, return cached value without resolving.
     * @param {Object} options.kwargs - Additional kwargs merged with resolver's _kw.
     * @returns {*} The resolved value (or Promise if load() is async).
     */
    resolve(options = {}) {
      const { static: isStatic = false, ...callKwargs } = options;
      if (isStatic) {
        return this._node ? this._node._value : this.cachedValue;
      }
      const kwargs = { ...this._kw };
      if (this._node && this._node.attr) {
        const internalParams = this.constructor.internalParams;
        for (const [key, value] of Object.entries(this._node.attr)) {
          if (!internalParams.has(key) && !(key in kwargs)) {
            kwargs[key] = value;
          }
        }
      }
      Object.assign(kwargs, callKwargs);
      const currentFingerprint = this._computeEffectiveFingerprint(kwargs);
      if (currentFingerprint === this._lastEffectiveFingerprint && !this.expired) {
        return this.cachedValue;
      }
      this._lastEffectiveFingerprint = currentFingerprint;
      const policy = getRetryPolicy(this);
      const doLoad = () => this.load(kwargs);
      if (policy) {
        return withRetry(doLoad, policy).then((value) => this._finalize(value));
      }
      const result = doLoad();
      if (result && typeof result.then === "function") {
        return result.then((value) => this._finalize(value));
      }
      return this._finalize(result);
    }
    /**
     * Finalize resolution: update cache timestamp and optionally store value.
     *
     * @param {*} value - The resolved value.
     * @returns {*} The value (possibly converted to Bag).
     * @private
     */
    _finalize(value) {
      let shouldConvert;
      if (this._asBag === true) {
        shouldConvert = true;
      } else if (this._asBag === false) {
        shouldConvert = false;
      } else {
        shouldConvert = !this._readOnly;
      }
      if (shouldConvert && value !== null && value !== void 0) {
        value = this._convertToBag(value);
      }
      this._lastUpdate = Date.now();
      if (!this.readOnly || this.cacheTime !== 0) {
        this.cachedValue = value;
      }
      return value;
    }
    /**
     * Convert result to Bag if possible.
     * Uses the Bag class registered via BagResolver.registerBagClass().
     *
     * @param {*} result - The value to convert.
     * @returns {*} A Bag if conversion succeeded, otherwise the original value.
     * @private
     */
    _convertToBag(result) {
      const BagClass = _BagResolver._BagClass;
      if (!BagClass) {
        return result;
      }
      if (result && typeof result._htraverse === "function") {
        return result;
      }
      if (typeof result === "string") {
        result = result.trim();
        if (result.startsWith("<") && BagClass.fromXml) {
          return BagClass.fromXml(result);
        }
        if ((result.startsWith("{") || result.startsWith("[")) && BagClass.fromJson) {
          return BagClass.fromJson(result);
        }
      }
      return result;
    }
    /**
     * Register the Bag class for asBag conversion.
     * Called by Bag module to avoid circular imports.
     *
     * @param {Function} BagClass - The Bag constructor.
     */
    static registerBagClass(BagClass) {
      _BagResolver._BagClass = BagClass;
    }
    /**
     * Load the value. Override in subclasses.
     *
     * Can return a value directly (sync) or a Promise (async).
     *
     * @param {Object} kwargs - Parameters for loading.
     * @returns {*} The loaded value or Promise.
     */
    load(kwargs) {
      return null;
    }
  };
  /**
   * Default options for this resolver class.
   * Subclasses can override to change defaults.
   */
  __publicField(_BagResolver, "classKwargs", {
    cacheTime: 0,
    readOnly: false,
    asBag: null,
    retryPolicy: null
  });
  /**
   * Positional argument names for constructor.
   * Subclasses can override to accept positional args.
   */
  __publicField(_BagResolver, "classArgs", []);
  /**
   * Parameters that are internal (not passed to load()).
   */
  __publicField(_BagResolver, "internalParams", /* @__PURE__ */ new Set(["cacheTime", "readOnly", "asBag", "retryPolicy"]));
  var BagResolver = _BagResolver;
  BagResolver._BagClass = null;
  var BagCbResolver = class extends BagResolver {
    /**
     * Create a callback resolver.
     *
     * @param {Object|Function} kwargs - Options or callback function directly.
     */
    constructor(kwargs = {}) {
      if (typeof kwargs === "function") {
        kwargs = { callback: kwargs };
      }
      super(kwargs);
      this._callback = kwargs.callback || null;
    }
    /**
     * Load by calling the callback.
     *
     * // DIFF-PYTHON: Python calls callback(**params) with expanded kwargs.
     * // JS calls callback(params) with a single kwargs object because JS
     * // has no **kwargs syntax. This is an intentional, unavoidable difference.
     *
     * @param {Object} kwargs - Parameters passed to callback as single object.
     * @returns {*} Result of callback (value or Promise).
     */
    load(kwargs) {
      if (!this._callback) {
        return null;
      }
      return this._callback.call(this, kwargs);
    }
  };
  __publicField(BagCbResolver, "classKwargs", {
    cacheTime: 0,
    readOnly: false,
    asBag: false,
    retryPolicy: null,
    callback: null
  });
  __publicField(BagCbResolver, "classArgs", ["callback"]);
  __publicField(BagCbResolver, "internalParams", /* @__PURE__ */ new Set(["cacheTime", "readOnly", "asBag", "retryPolicy", "callback"]));

  // src/bag-node.js
  var BagNode = class _BagNode {
    /**
     * Create a new BagNode.
     *
     * @param {Object} parentBag - The parent Bag containing this node.
     * @param {string} label - The node's key/name within the parent Bag.
     * @param {*} [value=null] - The node's value (can be scalar or Bag).
     * @param {Object} [attr=null] - Dict of attributes to set.
     * @param {BagResolver} [resolver=null] - Resolver for lazy value loading.
     * @param {string} [nodeTag=null] - Semantic type tag for the node.
     * @param {string} [xmlTag=null] - Original XML tag name (for serialization).
     * @param {boolean} [removeNullAttributes=true] - Remove null attributes during construction.
     */
    constructor(parentBag, label, value = null, attr = null, resolver = null, nodeTag = null, xmlTag = null, removeNullAttributes = true) {
      this.label = label;
      this._value = null;
      this._attr = {};
      this._parentBag = null;
      this._resolver = null;
      this._nodeSubscribers = {};
      this._onChangedValue = null;
      this.nodeTag = nodeTag;
      this.xmlTag = xmlTag;
      this._compiled = null;
      this.parentBag = parentBag;
      if (attr) {
        this.setAttr(attr, false, true, removeNullAttributes);
      }
      if (value !== null) {
        this.setValue(value, false);
      }
      if (resolver) {
        this.resolver = resolver;
      }
    }
    // -------------------------------------------------------------------------
    // Parent Bag Property
    // -------------------------------------------------------------------------
    get parentBag() {
      return this._parentBag;
    }
    set parentBag(parentBag) {
      if (parentBag === null && this._value?.parentNode === this) {
        this._value.setBackref();
      }
      this._parentBag = parentBag;
      if (parentBag?.backref && this._value && typeof this._value._htraverse === "function") {
        this._value.setBackref(this, parentBag);
      }
    }
    // -------------------------------------------------------------------------
    // Value Property and Methods
    // -------------------------------------------------------------------------
    get value() {
      return this.getValue();
    }
    set value(value) {
      this.setValue(value);
    }
    /**
     * Get the node's value.
     *
     * @param {boolean} [isStatic=false] - If true, return cached value without triggering resolver.
     * @param {string} [queryString=null] - Query string from path suffix (after '?').
     *   - null: return node value
     *   - '': return all attributes as an object
     *   - 'attr': return single attribute value (resolving attribute resolvers)
     *   - 'attr1&attr2': return tuple of attribute values
     *   - 'key=val::T&key2=val2::T': kwargs for resolver (parsed via tytx ::QS)
     * @param {Object} [kwargs={}] - Additional kwargs passed to resolver.
     * @returns {*} The value/attributes, or a Promise of the complete query result.
     * Static attribute queries preserve raw resolver objects without executing them.
     */
    getValue(isStatic = false, queryString = null, kwargs = {}) {
      if (queryString !== null) {
        const parsedQs = fromTytx(`${queryString}::QS`);
        if (Array.isArray(parsedQs)) {
          const keys = parsedQs.length ? parsedQs : Object.keys(this._attr);
          const values = keys.map((key) => {
            const value = this.getAttr(key);
            return !isStatic && value instanceof BagResolver ? value.resolve() : value;
          });
          const result = (attrs) => parsedQs.length === 0 ? Object.fromEntries(keys.map((key, index) => [key, attrs[index]])) : attrs.length === 1 ? attrs[0] : attrs;
          return values.some((value) => value && typeof value.then === "function") ? Promise.all(values).then(result) : result(values);
        } else {
          if (!this._resolver) {
            throw new Error("Cannot use kwargs syntax without resolver");
          }
          kwargs = { ...kwargs, ...parsedQs };
        }
      }
      if (this._resolver !== null) {
        return this._resolver.resolve({ static: isStatic, ...kwargs });
      }
      return this._value;
    }
    /**
     * Set the node's value.
     *
     * @param {*} value - The value to set.
     * @param {boolean} [trigger=true] - If true, notify subscribers of the change.
     * @param {Object} [attributes=null] - Optional attributes to set along with value.
     * @param {boolean|null} [updattr=null] - If falsy (default null), replace
     *   existing attributes; if true, merge. Note: unlike setAttr called
     *   directly (which merges by default), setValue replaces by default,
     *   matching Python's _updattr=None.
     * @param {boolean} [removeNullAttributes=true] - If true, remove null values from attributes.
     * @param {string} [reason=null] - Optional reason string for the trigger.
     */
    setValue(value, trigger = true, attributes = null, updattr = null, removeNullAttributes = true, reason = null) {
      if (value instanceof BagResolver) {
        this.resolver = value;
        value = null;
      } else if (value instanceof _BagNode) {
        attributes = attributes || {};
        Object.assign(attributes, value._attr);
        if (value.resolver) {
          this.resolver = value.resolver;
        }
        value = value._value;
      }
      const oldvalue = this._value;
      if (oldvalue !== value && oldvalue?.parentNode === this) {
        oldvalue.setBackref();
      }
      this._value = value;
      const valueChanged = oldvalue !== this._value;
      const callbackTrigger = trigger == null ? true : trigger;
      let attrsDiff = null;
      if (attributes !== null) {
        const oldattrSnapshot = { ...this._attr };
        this.setAttr(attributes, false, updattr, removeNullAttributes);
        const diff = this._buildAttrDiff(oldattrSnapshot, this._attr);
        attrsDiff = Object.keys(diff).length > 0 ? diff : null;
      }
      trigger = callbackTrigger && (valueChanged || attrsDiff !== null);
      const evt = attrsDiff ? valueChanged ? "upd_value_attr" : "upd_attrs" : "upd_value";
      if (this._onChangedValue) {
        this._onChangedValue(this, value, oldvalue, callbackTrigger);
      }
      if (trigger) {
        const info = attrsDiff !== null ? { oldvalue, attrs_diff: attrsDiff } : { oldvalue };
        for (const subscriber of Object.values(this._nodeSubscribers)) {
          subscriber({ node: this, info, evt });
        }
      }
      if (this._parentBag !== null && this._parentBag.backref) {
        if (value && typeof value._htraverse === "function") {
          value.setBackref(this, this._parentBag);
        }
        if (trigger) {
          this._parentBag._onNodeChanged(
            this,
            [this.label],
            evt,
            oldvalue,
            attrsDiff,
            reason
          );
        }
      }
    }
    /** Copy value, attributes and resolver; retain label, identity and position. */
    replace(other) {
      if (!(other instanceof _BagNode)) throw new TypeError("BagNode.replace expects a BagNode");
      if (other === this) return this;
      let value = other.staticValue;
      if (value && typeof value._htraverse === "function") {
        value = value.createChildBag().replace(value);
      }
      let resolver = null;
      if (other.resolver) {
        resolver = Object.create(
          Object.getPrototypeOf(other.resolver),
          Object.getOwnPropertyDescriptors(other.resolver)
        );
        resolver._node = null;
        resolver._kw = { ...other.resolver._kw };
      }
      const oldvalue = this._value;
      const oldattr = { ...this._attr };
      const oldresolver = this.resolver;
      if (oldresolver && oldresolver._node === this) oldresolver._node = null;
      this.resolver = resolver;
      this.setValue(value, false, { ...other.attr }, false, false, null);
      const diff = this._buildAttrDiff(oldattr, this._attr);
      const attrsDiff = Object.keys(diff).length ? diff : null;
      const valueChanged = oldvalue !== value || oldresolver !== resolver;
      if (valueChanged || attrsDiff) {
        const evt = attrsDiff ? valueChanged ? "upd_value_attr" : "upd_attrs" : "upd_value";
        const info = attrsDiff ? { oldvalue, attrs_diff: attrsDiff } : { oldvalue };
        for (const callback of Object.values(this._nodeSubscribers)) {
          callback({ node: this, info, evt });
        }
        if (this._parentBag !== null && this._parentBag.backref) {
          this._parentBag._onNodeChanged(this, [this.label], evt, oldvalue, attrsDiff);
        }
      }
      return this;
    }
    /**
     * Get node's raw _value (bypassing resolver).
     */
    get staticValue() {
      return this._value;
    }
    set staticValue(value) {
      this._value = value;
    }
    /**
     * Get the resolver attached to this node.
     *
     * @returns {BagResolver|null} The resolver or null.
     */
    get resolver() {
      return this._resolver;
    }
    /**
     * Set the resolver for this node.
     *
     * @param {BagResolver|null} resolver - The resolver to attach.
     */
    set resolver(resolver) {
      this._resolver = resolver;
      if (resolver && resolver.setNode) {
        resolver.setNode(this);
      }
    }
    /**
     * Reset the resolver and clear the node value.
     */
    resetResolver() {
      if (!this._resolver) {
        throw new Error("Cannot reset resolver: node has no resolver");
      }
      this._resolver.reset();
      this.setValue(null);
    }
    // -------------------------------------------------------------------------
    // Attribute Methods
    // -------------------------------------------------------------------------
    get attr() {
      return this._attr;
    }
    /**
     * Get attribute value or all attributes.
     *
     * @param {string} [label=null] - The attribute's label. If null, returns all attributes.
     * @param {*} [defaultValue=null] - Default value if attribute not found.
     * @returns {*} Attribute value, default, or dict of all attributes.
     */
    getAttr(label = null, defaultValue = null) {
      if (!label) {
        return this._attr;
      }
      return label in this._attr ? this._attr[label] : defaultValue;
    }
    /**
     * Compute the symmetric diff between two attribute snapshots.
     *
     * Returns a dict mapping each changed key to { old, new }, covering
     * added (old=null), removed (new=null) and modified entries. Keys whose
     * value did not change are omitted.
     *
     * @param {Object} oldattr - Attribute snapshot before the change.
     * @param {Object} newattr - Attribute snapshot after the change.
     * @returns {Object} Diff dict { name: { old, new } }.
     */
    _buildAttrDiff(oldattr, newattr) {
      const diff = {};
      const keys = /* @__PURE__ */ new Set([...Object.keys(oldattr), ...Object.keys(newattr)]);
      for (const key of keys) {
        const oldVal = key in oldattr ? oldattr[key] : null;
        const newVal = key in newattr ? newattr[key] : null;
        if (oldVal !== newVal) {
          diff[key] = { old: oldVal, new: newVal };
        }
      }
      return diff;
    }
    /**
     * Set attributes on the node.
     *
     * @param {Object} [attr=null] - Dictionary of attributes to set.
     * @param {boolean} [trigger=true] - If true, notify subscribers of the change.
     * @param {boolean} [updattr=true] - If false, clear existing attributes first.
     * @param {boolean} [removeNullAttributes=true] - If true, remove null values from attributes.
     */
    setAttr(attr = null, trigger = true, updattr = true, removeNullAttributes = true) {
      const newAttr = attr || {};
      const hasNodeSubscribers = Object.keys(this._nodeSubscribers).length > 0;
      const needDiff = trigger && (hasNodeSubscribers || this._parentBag !== null && this._parentBag.backref);
      const oldattr = needDiff ? { ...this._attr } : null;
      if (updattr) {
        Object.assign(this._attr, newAttr);
      } else {
        this._attr = { ...newAttr };
      }
      if (removeNullAttributes) {
        for (const key of Object.keys(this._attr)) {
          if (this._attr[key] === null) {
            delete this._attr[key];
          }
        }
      }
      if (trigger && oldattr !== null) {
        const diff = this._buildAttrDiff(oldattr, this._attr);
        if (Object.keys(diff).length > 0 && hasNodeSubscribers) {
          for (const subscriber of Object.values(this._nodeSubscribers)) {
            subscriber({ node: this, info: { attrs_diff: diff }, evt: "upd_attrs" });
          }
        }
        if (Object.keys(diff).length > 0 && this._parentBag !== null && this._parentBag.backref) {
          const reason = trigger === true ? "true" : String(trigger);
          this._parentBag._onNodeChanged(
            this,
            [this.label],
            "upd_attrs",
            null,
            diff,
            reason
          );
        }
      }
    }
    /**
     * Delete attributes from the node.
     *
     * @param {...string} attrsToDelete - Attribute labels to remove.
     *   Each can be a single label or a comma-separated string.
     */
    delAttr(...attrsToDelete) {
      for (const attr of attrsToDelete) {
        if (typeof attr === "string" && attr.includes(",")) {
          for (const a of attr.split(",")) {
            delete this._attr[a.trim()];
          }
        } else {
          delete this._attr[attr];
        }
      }
    }
    /**
     * Check if a node has the given attribute.
     *
     * @param {string} label - Attribute label to check.
     * @param {*} [value=null] - If provided, also check if attribute has this value.
     * @returns {boolean} True if attribute exists (and matches value if provided).
     */
    hasAttr(label, value = null) {
      if (!(label in this._attr)) {
        return false;
      }
      if (value !== null) {
        return this._attr[label] === value;
      }
      return true;
    }
    /**
     * Get attributes inherited from ancestors.
     *
     * @returns {Object} Dict with all inherited attributes merged with this node's attributes.
     */
    getInheritedAttributes() {
      let inherited = {};
      if (this._parentBag && this._parentBag.parentNode) {
        inherited = this._parentBag.parentNode.getInheritedAttributes();
      }
      return { ...inherited, ...this._attr };
    }
    // -------------------------------------------------------------------------
    // Subscription Methods
    // -------------------------------------------------------------------------
    /**
     * Subscribe to changes on this specific node.
     *
     * @param {string} subscriberId - Unique identifier for this subscription.
     * @param {Function} callback - Function to call on changes.
     *
     * Callback signature: callback({ node, info, evt })
     * - node: This BagNode
     * - info: an object with semantic keys:
     *     - 'upd_value'      → { oldvalue }
     *     - 'upd_attrs'      → { attrs_diff }   (diff dict { name: { old, new } })
     *     - 'upd_value_attr' → { oldvalue, attrs_diff }
     * - evt: Event type ('upd_value', 'upd_attrs' or 'upd_value_attr')
     */
    subscribe(subscriberId, callback) {
      this._nodeSubscribers[subscriberId] = callback;
    }
    /**
     * Unsubscribe from changes on this node.
     *
     * @param {string} subscriberId - The subscription identifier to remove.
     */
    unsubscribe(subscriberId) {
      delete this._nodeSubscribers[subscriberId];
    }
    // -------------------------------------------------------------------------
    // Compilation Properties
    // -------------------------------------------------------------------------
    /**
     * Lazy-initialized compiled data storage.
     * External systems (compilers) store compiled data here.
     *
     * @returns {Object} The compiled data dictionary.
     */
    get compiled() {
      if (!this._compiled) {
        this._compiled = {};
      }
      return this._compiled;
    }
    /**
     * Check if this node's value is a Bag (branch node).
     * Uses duck typing via _htraverse to avoid circular import.
     *
     * @returns {boolean} True if value is a Bag.
     */
    get isBranch() {
      return this._value != null && typeof this._value._htraverse === "function";
    }
    // -------------------------------------------------------------------------
    // Navigation Properties
    // -------------------------------------------------------------------------
    /**
     * Get this node's index position within parent Bag.
     *
     * @returns {number|null} The 0-based index of this node in the parent's node list,
     *   or null if this node has no parent.
     */
    get position() {
      if (this._parentBag === null) {
        return null;
      }
      return this._parentBag._nodes.index(this.label);
    }
    /**
     * Get dot-separated path from root to this node.
     *
     * @returns {string|null} Full path or null if no parent.
     */
    get fullpath() {
      if (this._parentBag !== null) {
        const parentFullpath = this._parentBag.fullpath;
        return parentFullpath ? `${parentFullpath}.${this.label}` : this.label;
      }
      return null;
    }
    /**
     * Get the node that contains this node's parent Bag.
     *
     * In the hierarchy: grandparent_bag contains parent_node, whose value
     * is parent_bag, which contains this node.
     *
     * @returns {BagNode|null} The parent node or null.
     */
    get parentNode() {
      if (this._parentBag) {
        return this._parentBag.parentNode;
      }
      return null;
    }
    /**
     * Find the ancestor node that owns a given attribute.
     *
     * @param {string} attrname - Attribute name to search for.
     * @param {*} [attrvalue=null] - If provided, also match this value.
     * @returns {BagNode|null} The node that owns the attribute, or null.
     */
    attributeOwnerNode(attrname, attrvalue = null) {
      let curr = this;
      if (attrvalue === null) {
        while (curr && !(attrname in curr._attr)) {
          curr = curr.parentNode;
        }
      } else {
        while (curr && curr._attr[attrname] !== attrvalue) {
          curr = curr.parentNode;
        }
      }
      return curr;
    }
    /**
     * Return node data as a tuple (array).
     *
     * @returns {Array} Array of [label, value, attr, resolver].
     */
    asTuple() {
      return [this.label, this.value, this._attr, this._resolver || null];
    }
    // -------------------------------------------------------------------------
    // Comparison
    // -------------------------------------------------------------------------
    /**
     * Check equality with another BagNode.
     *
     * @param {BagNode} other - Node to compare with.
     * @returns {boolean} True if label, attr and value match.
     */
    isEqual(other) {
      if (!(other instanceof _BagNode)) {
        return false;
      }
      if (this.label !== other.label) {
        return false;
      }
      const thisKeys = Object.keys(this._attr);
      const otherKeys = Object.keys(other._attr);
      if (thisKeys.length !== otherKeys.length) {
        return false;
      }
      for (const key of thisKeys) {
        if (this._attr[key] !== other._attr[key]) {
          return false;
        }
      }
      if (this._resolver !== null) {
        return this._resolver === other._resolver;
      }
      if (this._value && typeof this._value.equalTo === "function") {
        return this._value.equalTo(other._value);
      }
      if (this._value && typeof this._value.isEqual === "function") {
        return this._value.isEqual(other._value);
      }
      return this._value === other._value;
    }
    /**
     * Compare this node with another and return differences.
     *
     * @param {BagNode} other - Another BagNode to compare with.
     * @returns {string|null} Description of differences, or null if equal.
     */
    diff(other) {
      if (this.label !== other.label) {
        return `Other label: ${other.label}`;
      }
      const thisKeys = Object.keys(this._attr);
      const otherKeys = Object.keys(other._attr);
      if (thisKeys.length !== otherKeys.length || thisKeys.some((k) => this._attr[k] !== other._attr[k])) {
        return `attributes self:${JSON.stringify(this._attr)} --- other:${JSON.stringify(other._attr)}`;
      }
      if (this._value !== other._value) {
        return `value self:${this._value} --- other:${other._value}`;
      }
      return null;
    }
    /**
     * Convert node to JSON-serializable dict.
     *
     * @param {boolean} [typed=true] - If true, include type information.
     * @returns {Object} Dict with keys 'label', 'value', and 'attr'.
     */
    toJson(typed = true) {
      let value = this.value;
      if (value && typeof value.toJson === "function") {
        value = value.toJson(typed, true);
      }
      return { label: this.label, value, attr: this._attr };
    }
    // -------------------------------------------------------------------------
    // String representation
    // -------------------------------------------------------------------------
    toString() {
      return `BagNode : ${this.label}`;
    }
  };

  // src/bag-node-container.js
  var BagNodeContainer = class _BagNodeContainer {
    constructor() {
      this._dict = /* @__PURE__ */ Object.create(null);
      this._list = [];
      this._parentBag = null;
    }
    /**
     * Return the index of a label in this container.
     *
     * @param {string} label - The label or special syntax to look up.
     *   - 'label': exact label match
     *   - '#n': numeric index (e.g., '#0', '#1')
     *   - '#attr=value': find by attribute value (e.g., '#id=34')
     *   - '#=value': find by node value (e.g., '#=target')
     * @returns {number} Index position (0-based), or -1 if not found.
     */
    index(label) {
      if (label in this._dict) {
        return this._list.findIndex((node) => node.label === label);
      }
      let match = label.match(/^#(\d+)$/);
      if (match) {
        const idx = parseInt(match[1], 10);
        return idx < this._list.length ? idx : -1;
      }
      match = label.match(/^#(\w*)=(.*)$/);
      if (match) {
        const [, attr, rawValue] = match;
        const value = rawValue.includes("::") ? fromTytx(rawValue) : rawValue;
        if (attr) {
          return this._list.findIndex((node) => node.getAttr(attr) === value);
        } else {
          return this._list.findIndex((node) => node._value === value);
        }
      }
      return -1;
    }
    /**
     * Parse position syntax and return insertion index.
     *
     * Supported formats:
     *   - null or '>': append at end
     *   - '<': insert at beginning
     *   - int n: insert at index n. Negative values count from the end
     *     (Python-style: -1 = before last). Out-of-range values clamp to [0, len].
     *   - '#n': insert at non-negative index n (clamped to len)
     *   - '<label': insert before node with given label
     *   - '>label': insert after node with given label
     *   - '<#n' / '>#n': insert before/after non-negative index n
     *
     * Fails fast on malformed input instead of silently appending, so a bad
     * position is reported to the caller (aligns with Python _parse_position).
     *
     * @param {string|number|null} position - Position specification.
     * @returns {number} Index where to insert (always valid for splice).
     * @throws {Error} If the string position is malformed (e.g. '#abc', '#-1',
     *   '@foo') or references a non-existent label (e.g. '<missing').
     */
    _parsePosition(position) {
      const n = this._list.length;
      if (position === null || position === void 0 || position === ">") {
        return n;
      }
      if (typeof position === "number") {
        if (position < 0) {
          position = n + position;
        }
        return Math.max(0, Math.min(position, n));
      }
      if (position === "<") {
        return 0;
      }
      if (position.startsWith("#")) {
        const idx = this._parseSharpIndex(position.slice(1), position);
        return Math.min(idx, n);
      }
      if (position.startsWith("<")) {
        const ref = position.slice(1);
        if (ref.startsWith("#")) {
          const idx = this._parseSharpIndex(ref.slice(1), position);
          return Math.min(idx, n);
        }
        const labelIdx = this.index(ref);
        if (labelIdx < 0) {
          throw new Error(
            `Invalid node_position '${position}': label '${ref}' not found`
          );
        }
        return labelIdx;
      }
      if (position.startsWith(">")) {
        const ref = position.slice(1);
        if (ref.startsWith("#")) {
          const idx = this._parseSharpIndex(ref.slice(1), position);
          return Math.min(idx + 1, n);
        }
        const labelIdx = this.index(ref);
        if (labelIdx < 0) {
          throw new Error(
            `Invalid node_position '${position}': label '${ref}' not found`
          );
        }
        return labelIdx + 1;
      }
      throw new Error(`Invalid node_position '${position}': unrecognized syntax`);
    }
    /**
     * Parse a non-negative integer from '#n' syntax.
     *
     * @param {string} raw - The part after '#' (e.g. '3' from '#3').
     * @param {string} original - Full position string for error messages.
     * @returns {number} The parsed non-negative integer.
     * @throws {Error} If raw is not a non-negative integer.
     */
    _parseSharpIndex(raw, original) {
      if (!/^-?\d+$/.test(raw)) {
        throw new Error(
          `Invalid node_position '${original}': '${raw}' is not an integer`
        );
      }
      const idx = parseInt(raw, 10);
      if (idx < 0) {
        throw new Error(
          `Invalid node_position '${original}': negative index not allowed in '#n' syntax`
        );
      }
      return idx;
    }
    /**
     * Get item by label or index.
     *
     * @param {string|number} key - Label string or integer index.
     * @returns {BagNode|null} The BagNode if found, null otherwise.
     */
    get(key) {
      if (typeof key === "number") {
        return key >= 0 && key < this._list.length ? this._list[key] : null;
      }
      if (key.startsWith("#")) {
        const idx = this.index(key);
        return idx >= 0 ? this._list[idx] : null;
      }
      return this._dict[key] || null;
    }
    /**
     * Set or create a BagNode with optional position.
     *
     * Supports ?attr syntax to set attributes instead of value (always
     * merged with existing attributes, regardless of `updattr`):
     *   - 'label?myattr' → sets attribute 'myattr' to value
     *   - 'label?x&y&z' → sets attributes from tuple (value must be array with matching length)
     *
     * @param {string} label - The node label. Can contain ?attr suffix.
     * @param {*} value - The value to set. With ?attr syntax, becomes the attribute value.
     * @param {string|number|null} [nodePosition='>'] - Position specification.
     * @param {Object} [attr=null] - Optional attributes.
     * @param {Object} [parentBag=null] - Parent Bag reference.
     * @param {BagResolver} [resolver=null] - Resolver to attach to node.
     * @param {boolean} [updattr=false] - If false, clear existing attributes first.
     * @param {boolean} [removeNullAttributes=true] - If true, remove null values from attributes.
     * @param {string} [reason=null] - Optional reason string for events.
     * @param {boolean} [doTrigger=true] - If false, suppress events.
     * @param {boolean} [fired=false] - If true, reset value to null after creation.
     * @param {string} [nodeTag=null] - Semantic type tag for the node.
     * @returns {BagNode} The created or updated BagNode.
     */
    set(label, value, nodePosition = ">", attr = null, parentBag = null, resolver = null, updattr = false, removeNullAttributes = true, reason = null, doTrigger = true, fired = false, nodeTag = null) {
      let queryString = null;
      if (label.includes("?")) {
        [label, queryString] = label.split("?", 2);
      }
      if (label === null || label === void 0 || label.startsWith("#")) {
        throw new Error("Cannot create new node with #n syntax");
      }
      if (queryString) {
        const qs = queryString.split("&");
        if (qs.length === 1) {
          attr = { [qs[0]]: value };
        } else {
          if (!Array.isArray(value) || value.length !== qs.length) {
            throw new Error("Wrong attributes assignment");
          }
          attr = {};
          for (let i = 0; i < qs.length; i++) {
            attr[qs[i]] = value[i];
          }
        }
        value = null;
      }
      let node = this._dict[label];
      if (node) {
        if (nodeTag) {
          node.nodeTag = nodeTag;
        }
        if (resolver !== null) {
          if (resolver === false) {
            node.resolver = null;
          } else {
            node.resolver = resolver;
          }
        }
        if (queryString) {
          node.setAttr(attr, doTrigger, true, removeNullAttributes);
        } else {
          node.setValue(value, doTrigger, attr, updattr, removeNullAttributes, reason);
        }
      } else {
        const NodeClass = parentBag && parentBag.nodeClass ? parentBag.nodeClass : BagNode;
        node = new NodeClass(
          parentBag,
          label,
          queryString ? null : value,
          attr,
          resolver,
          nodeTag,
          null,
          removeNullAttributes
        );
        const idx = this._parsePosition(nodePosition);
        this._dict[label] = node;
        this._list.splice(idx, 0, node);
        if (doTrigger && parentBag && parentBag.backref) {
          parentBag._onNodeInserted(node, idx, null, reason);
        }
      }
      if (fired) {
        node.setValue(null, false);
      }
      return node;
    }
    /**
     * Remove and return item.
     *
     * @param {string|number} key - Label, index, or '#n'.
     * @returns {BagNode|null} The removed BagNode, or null if not found.
     */
    pop(key) {
      const node = this.get(key);
      if (node) {
        delete this._dict[node.label];
        const idx = this._list.indexOf(node);
        if (idx >= 0) {
          this._list.splice(idx, 1);
        }
        return node;
      }
      return null;
    }
    /**
     * Check if label exists.
     *
     * @param {string} key - Label to check.
     * @returns {boolean} True if label exists.
     */
    has(key) {
      return key in this._dict;
    }
    /**
     * Return number of elements.
     *
     * @returns {number} Number of elements.
     */
    get length() {
      return this._list.length;
    }
    /**
     * Clear all elements.
     */
    clear() {
      this._dict = /* @__PURE__ */ Object.create(null);
      this._list = [];
    }
    /**
     * Return node labels in order.
     *
     * @returns {string[]} Array of labels.
     */
    keys() {
      return this._list.map((node) => node.label);
    }
    /**
     * Return node values in order.
     *
     * @returns {Array} Array of values.
     */
    values() {
      return this._list.map((node) => node.getValue());
    }
    /**
     * Return [label, value] tuples in order.
     *
     * @returns {Array} Array of [label, value] tuples.
     */
    items() {
      return this._list.map((node) => [node.label, node.getValue()]);
    }
    /**
     * Make container iterable.
     */
    [Symbol.iterator]() {
      return this._list[Symbol.iterator]();
    }
    /**
     * Move element(s) to a new position.
     *
     * @param {number|number[]} what - Index or list of indices to move.
     * @param {number} position - Target index position.
     * @param {boolean} [trigger=true] - If true, fire del/ins events.
     */
    move(what, position, trigger = true) {
      if (position < 0) {
        return;
      }
      const indices = Array.isArray(what) ? what : [what];
      if (indices.length === 0) {
        return;
      }
      if (position >= this._list.length) {
        return;
      }
      const destLabel = this._list[position].label;
      if (indices.length > 1) {
        const sortedIndices = [...indices].sort((a, b) => a - b);
        const delta = sortedIndices[0] < position ? 1 : 0;
        const popped = [];
        for (let i = sortedIndices.length - 1; i >= 0; i--) {
          const idx = sortedIndices[i];
          if (idx >= 0 && idx < this._list.length) {
            const node = this._list[idx];
            this._list.splice(idx, 1);
            popped.push(node);
            if (trigger && this._parentBag && this._parentBag.backref) {
              this._parentBag._onNodeDeleted(node, idx);
            }
          }
        }
        let newPos = this.index(destLabel);
        if (newPos < 0) {
          newPos = this._list.length;
        }
        newPos += delta;
        for (const node of popped) {
          this._list.splice(newPos, 0, node);
          if (trigger && this._parentBag && this._parentBag.backref) {
            this._parentBag._onNodeInserted(node, newPos);
          }
        }
      } else {
        const fromIdx = indices[0];
        if (fromIdx === position) {
          return;
        }
        if (fromIdx < 0 || fromIdx >= this._list.length) {
          return;
        }
        const node = this._list[fromIdx];
        this._list.splice(fromIdx, 1);
        if (trigger && this._parentBag && this._parentBag.backref) {
          this._parentBag._onNodeDeleted(node, fromIdx);
        }
        this._list.splice(position, 0, node);
        if (trigger && this._parentBag && this._parentBag.backref) {
          this._parentBag._onNodeInserted(node, position);
        }
      }
    }
    /**
     * Check equality with another BagNodeContainer.
     *
     * @param {BagNodeContainer} other - Container to compare with.
     * @returns {boolean} True if equal (same nodes in same order).
     */
    isEqual(other) {
      if (!(other instanceof _BagNodeContainer)) {
        return false;
      }
      if (this._list.length !== other._list.length) {
        return false;
      }
      for (let i = 0; i < this._list.length; i++) {
        const thisNode = this._list[i];
        const otherNode = other._list[i];
        if (!thisNode.isEqual(otherNode)) {
          return false;
        }
      }
      return true;
    }
  };

  // src/bag.js
  var import_xmldom = __toESM(require_lib(), 1);

  // src/resolver-wire.js
  var MARKER = "::RSLV:";
  var registrations = /* @__PURE__ */ new Map();
  var classes = /* @__PURE__ */ new Map();
  var opaquePayloads = /* @__PURE__ */ new WeakMap();
  var BagSerializationError = class extends Error {
    constructor(message) {
      super(message);
      this.name = "BagSerializationError";
    }
  };
  var OpaqueResolver = class extends BagResolver {
    constructor(payload) {
      super({ asBag: false });
      opaquePayloads.set(this, payload);
    }
    get payload() {
      return opaquePayloads.get(this);
    }
    load() {
      throw new BagSerializationError("This resolver is opaque; local execution is unavailable");
    }
  };
  function registerResolver(cls, { module, name, encode, decode }) {
    if (!(cls.prototype instanceof BagResolver) || cls === OpaqueResolver || typeof module !== "string" || !module || typeof name !== "string" || !name || typeof encode !== "function" || typeof decode !== "function") {
      throw new TypeError("registerResolver requires a BagResolver subclass, module, name and adapters");
    }
    const key = JSON.stringify([module, name]);
    if (registrations.has(key) && registrations.get(key).cls !== cls) {
      throw new TypeError(`Resolver ${module}.${name} is already registered`);
    }
    if (classes.has(cls) && classes.get(cls).key !== key) {
      throw new TypeError("A resolver class cannot own two wire identities");
    }
    const entry = { cls, module, name, encode, decode, key };
    registrations.set(key, entry);
    classes.set(cls, entry);
  }
  function validateDescription(data) {
    if (!data || typeof data !== "object" || Array.isArray(data) || typeof data.resolver_module !== "string" || typeof data.resolver_class !== "string" || !Array.isArray(data.args ?? []) || !data.kwargs || typeof data.kwargs !== "object" || Array.isArray(data.kwargs)) {
      throw new BagSerializationError("Invalid resolver description");
    }
  }
  function validateJson(value, parents = /* @__PURE__ */ new Set()) {
    if (value === null || typeof value === "string" || typeof value === "boolean") return;
    if (typeof value === "number" && Number.isFinite(value)) return;
    if (typeof value !== "object" || parents.has(value) || !Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) {
      throw new BagSerializationError("Resolver parameters must be JSON data; callbacks cannot travel");
    }
    parents.add(value);
    for (const child of Object.values(value)) validateJson(child, parents);
    parents.delete(value);
  }
  function encodeResolver(resolver) {
    if (opaquePayloads.has(resolver)) return opaquePayloads.get(resolver);
    const entry = classes.get(resolver.constructor);
    if (!entry) throw new BagSerializationError(`Unregistered resolver: ${resolver.constructor.name}`);
    const parameters = entry.encode(resolver);
    const data = {
      resolver_module: entry.module,
      resolver_class: entry.name,
      args: parameters.args ?? [],
      kwargs: parameters.kwargs ?? {}
    };
    validateDescription(data);
    validateJson(data);
    return MARKER + JSON.stringify(data);
  }
  function decodeResolver(value) {
    if (typeof value !== "string" || !value.startsWith(MARKER)) return null;
    const payload = value.slice(MARKER.length);
    if (/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+$/.test(payload)) {
      return new OpaqueResolver(value);
    }
    let data;
    try {
      data = JSON.parse(payload);
    } catch {
      throw new BagSerializationError("Invalid resolver JSON or signed token");
    }
    validateDescription(data);
    const entry = registrations.get(JSON.stringify([data.resolver_module, data.resolver_class]));
    if (!entry) return new OpaqueResolver(value);
    const resolver = entry.decode({ args: data.args ?? [], kwargs: data.kwargs });
    if (!(resolver instanceof entry.cls)) {
      throw new BagSerializationError("Resolver decoder returned an incompatible instance");
    }
    return resolver;
  }
  function encodeAttrs(attr) {
    return Object.fromEntries(Object.entries(attr || {}).map(([key, value]) => [key, value instanceof BagResolver ? encodeResolver(value) : value]));
  }
  function decodeAttrs(attr) {
    return Object.fromEntries(Object.entries(attr || {}).map(([key, value]) => [key, decodeResolver(value) ?? value]));
  }

  // src/bag.js
  function* serializationNodes(bag, prefix = "") {
    for (const node of bag) {
      const path = prefix ? `${prefix}.${node.label}` : node.label;
      yield [path, node];
      const value = node.getValue(true);
      if (!node.resolver && value instanceof Bag) yield* serializationNodes(value, path);
    }
  }
  var _Bag = class _Bag {
    /**
     * Create a new Bag.
     *
     * @param {Object} [source=null] - Optional dict to initialize from.
     */
    constructor(source = null) {
      this._nodes = new BagNodeContainer();
      this._backref = false;
      this._parent = null;
      this._parentNode = null;
      this._rootAttributes = null;
      this._updSubscribers = {};
      this._insSubscribers = {};
      this._delSubscribers = {};
      if (source) {
        this._loadSource(source);
      }
    }
    // -------------------------------------------------------------------------
    // Properties
    // -------------------------------------------------------------------------
    get parent() {
      return this._parent;
    }
    set parent(value) {
      this._parent = value;
    }
    get parentNode() {
      return this._parentNode;
    }
    set parentNode(value) {
      this._parentNode = value;
    }
    get backref() {
      return Boolean(this._backref);
    }
    /**
     * Node class used to create new nodes. Override in subclasses
     * to use custom BagNode subclasses.
     *
     * @returns {Function} The BagNode constructor.
     */
    get nodeClass() {
      return BagNode;
    }
    createChildBag() {
      return new this.constructor();
    }
    /**
     * Full path from root Bag to this Bag.
     *
     * Returns the dot-separated path from the root of the hierarchy to this
     * Bag. Returns null if backref mode is not enabled or if this is the root.
     *
     * @returns {string|null} The full path or null.
     */
    get fullpath() {
      if (this._parent !== null && this._parentNode !== null) {
        const parentFullpath = this._parent.fullpath;
        if (parentFullpath) {
          return `${parentFullpath}.${this._parentNode.label}`;
        } else {
          return this._parentNode.label;
        }
      }
      return null;
    }
    /**
     * Get dot-separated path from this Bag to a descendant node.
     *
     * Walks up from the node to this Bag collecting labels.
     * Requires backref mode enabled.
     *
     * @param {BagNode} node - A descendant BagNode.
     * @returns {string|null} The relative path, or null if not a descendant.
     */
    relativePath(node) {
      const parts = [];
      let current = node;
      while (current !== null) {
        if (current.parentBag === this) {
          parts.push(current.label);
          parts.reverse();
          return parts.join(".");
        }
        parts.push(current.label);
        current = current.parentNode;
      }
      return null;
    }
    get length() {
      return this._nodes.length;
    }
    /**
     * Root Bag of the hierarchy.
     *
     * Traverses the parent chain to find the topmost Bag. If this Bag has no
     * parent, returns itself.
     *
     * @returns {Bag} The root Bag.
     */
    get root() {
      let curr = this;
      while (curr.parent !== null) {
        curr = curr.parent;
      }
      return curr;
    }
    /**
     * Attributes of the node containing this Bag.
     *
     * Returns the attributes of the parent node that contains this Bag.
     * Returns an empty object if this Bag has no parent node.
     *
     * @returns {Object} Attributes dictionary.
     */
    get attributes() {
      if (this._parentNode !== null) {
        return this._parentNode.getAttr();
      }
      return {};
    }
    /**
     * Root-level attributes for this Bag hierarchy.
     *
     * These are special attributes stored at the hierarchy level,
     * independent of any node attributes.
     *
     * @returns {Object|null} Root attributes or null.
     */
    get rootAttributes() {
      return this._rootAttributes;
    }
    set rootAttributes(attrs) {
      this._rootAttributes = attrs !== null ? { ...attrs } : null;
    }
    // -------------------------------------------------------------------------
    // _htraverse helpers
    // -------------------------------------------------------------------------
    /**
     * Parse path and handle #parent navigation.
     *
     * @param {string|Array} path - Dot-separated path or array of segments.
     * @returns {Array} Tuple of [curr, pathlist].
     */
    _htraverseBefore(path) {
      let curr = this;
      let pathlist;
      if (typeof path === "string") {
        path = path.replace(/\.\.\//g, "#parent.");
        pathlist = path.split(".").filter((x) => x);
      } else {
        pathlist = [...path];
      }
      while (pathlist.length && pathlist[0] === "#parent" && curr !== null) {
        pathlist.shift();
        curr = curr.parent;
      }
      return [curr, pathlist];
    }
    // -------------------------------------------------------------------------
    // _htraverse
    // -------------------------------------------------------------------------
    /**
     * Traverse a hierarchical path.
     *
     * A `#parent` segment (also the `../` alias, expanded by _htraverseBefore)
     * walks up to the parent Bag. It is handled both as a leading segment and
     * inside the path; it requires backref/parent to be set, otherwise the
     * traversal breaks (read → null; write → stops short).
     *
     * @param {string|Array} path - Path as dot-separated string or array.
     * @param {boolean} [writeMode=false] - If true, create intermediate Bags.
     * @param {boolean} [isStatic=true] - If true, don't trigger resolvers.
     * @returns {Array} Tuple of [container, label].
     */
    _htraverse(path, writeMode = false, isStatic = true) {
      let [curr, pathlist] = this._htraverseBefore(path);
      if (curr === null) {
        return [null, null];
      }
      if (pathlist.length === 0) {
        return [curr, ""];
      }
      while (pathlist.length > 1 && curr instanceof _Bag) {
        const segment = pathlist[0];
        if (segment === "#parent") {
          if (curr.parent === null || curr.parent === void 0) {
            break;
          }
          pathlist.shift();
          curr = curr.parent;
          continue;
        }
        const node = curr._nodes.get(segment);
        if (!node) {
          break;
        }
        const value = node.getValue(isStatic);
        if (value instanceof _Bag) {
          pathlist.shift();
          curr = value;
        } else if (writeMode) {
          const newBag = curr.createChildBag();
          node.setValue(newBag, true, null, true, true, "autocreate");
          pathlist.shift();
          curr = newBag;
        } else {
          break;
        }
      }
      if (!writeMode) {
        if (pathlist.length > 1) {
          return [null, null];
        }
        return [curr, pathlist[0]];
      }
      while (pathlist.length > 1) {
        const label = pathlist.shift();
        if (label.startsWith("#")) {
          throw new BagException("Not existing index in #n syntax");
        }
        const newBag = curr.createChildBag();
        curr._nodes.set(label, newBag, ">", null, curr, null, false, true, "autocreate");
        curr = newBag;
      }
      return [curr, pathlist[0]];
    }
    // -------------------------------------------------------------------------
    // get (single level)
    // -------------------------------------------------------------------------
    /**
     * Get value at a single level (no path traversal).
     *
     * @param {string} label - Node label to look up.
     * @param {*} [defaultValue=null] - Value to return if label not found.
     * @param {boolean} [isStatic=true] - If true, don't trigger resolvers.
     * @param {Object} [kwargs={}] - Additional kwargs passed to resolver.
     * @returns {*} The node's value if found, otherwise default.
     */
    get(label, defaultValue = null, isStatic = true, kwargs = {}) {
      if (!label) {
        return this;
      }
      if (label === "#parent") {
        return this.parent;
      }
      let queryString = null;
      if (label.includes("?")) {
        [label, queryString] = label.split("?", 2);
      }
      const node = this._nodes.get(label);
      if (!node) {
        return defaultValue;
      }
      return node.getValue(isStatic, queryString, kwargs);
    }
    // -------------------------------------------------------------------------
    // getItem
    // -------------------------------------------------------------------------
    /**
     * Get value at a hierarchical path.
     *
     * @param {string} path - Hierarchical path like 'a.b.c'.
     * @param {*} [defaultValue=null] - Value to return if path not found.
     * @param {boolean} [isStatic=false] - If true, don't trigger resolvers.
     * @param {Object} [kwargs={}] - Additional kwargs passed to resolver at final path.
     * @returns {*} The value at the path if found, otherwise default.
     */
    getItem(path, defaultValue = null, isStatic = false, kwargs = {}) {
      if (!path) {
        return this;
      }
      const [obj, label] = this._htraverse(path, false, isStatic);
      if (obj instanceof _Bag) {
        return obj.get(label, defaultValue, isStatic, kwargs);
      }
      return defaultValue;
    }
    // -------------------------------------------------------------------------
    // setItem
    // -------------------------------------------------------------------------
    /**
     * Set value at a hierarchical path.
     *
     * An empty path raises RangeError without modifying the Bag.
     *
     * Resolver handling:
     *   - resolver=null (default): throw if node already has a resolver
     *   - resolver=false: remove existing resolver and set value
     *   - resolver=BagResolver: replace resolver
     *
     * @param {string} path - Hierarchical path like 'a.b.c'.
     * @param {*} value - Value to set at the path.
     * @param {Object} [attr=null] - Optional attributes to set on the node.
     * @param {string|number|null} [nodePosition='>'] - Position for new nodes.
     * @param {boolean} [updattr=false] - If false, clear existing attributes first.
     * @param {boolean} [removeNullAttributes=true] - If true, remove null values from attributes.
     * @param {string} [reason=null] - Reason for the change (for events).
     * @param {boolean} [fired=false] - If true, reset value to null after setting.
     * @param {boolean} [doTrigger=true] - If false, suppress events.
     * @param {*} [resolver=null] - Resolver handling for existing nodes.
     * @param {string} [nodeTag=null] - Semantic type tag for the node.
     * @returns {BagNode} The created or updated BagNode.
     */
    setItem(path, value, attr = null, nodePosition = ">", updattr = false, removeNullAttributes = true, reason = null, fired = false, doTrigger = true, resolver = null, nodeTag = null) {
      if (path === "") {
        throw new RangeError("setItem requires a non-empty path");
      }
      const [obj, label] = this._htraverse(path, true);
      return obj._nodes.set(
        label,
        value,
        nodePosition,
        attr,
        obj,
        resolver,
        updattr,
        removeNullAttributes,
        reason,
        doTrigger,
        fired,
        nodeTag
      );
    }
    // -------------------------------------------------------------------------
    // _pop (internal)
    // -------------------------------------------------------------------------
    /**
     * Internal pop by label at current level.
     *
     * @param {string} label - Node label to remove.
     * @param {string|null} [reason=null] - Reason for deletion (for events).
     * @returns {BagNode|null} The removed BagNode, or null if not found.
     */
    _pop(label, reason = null) {
      const p = this._nodes.index(label);
      if (p >= 0) {
        const node = this._nodes.pop(p);
        if (this.backref) {
          this._onNodeDeleted(node, p, reason);
        }
        return node;
      }
      return null;
    }
    // -------------------------------------------------------------------------
    // pop
    // -------------------------------------------------------------------------
    /**
     * Remove a node and return its value.
     *
     * Traverses to the path, removes the node, and returns its value.
     *
     * @param {string} path - Hierarchical path to the node to remove.
     * @param {*} [defaultValue=null] - Value to return if path not found.
     * @param {string|null} [reason=null] - Reason for deletion (for events).
     * @returns {*} The value of the removed node, or default if not found.
     */
    pop(path, defaultValue = null, reason = null) {
      const node = this.popNode(path, reason);
      return node ? node.value : defaultValue;
    }
    /**
     * Alias for pop.
     */
    delItem(path, defaultValue = null, reason = null) {
      return this.pop(path, defaultValue, reason);
    }
    // -------------------------------------------------------------------------
    // popNode
    // -------------------------------------------------------------------------
    /**
     * Remove and return the BagNode at a path.
     *
     * Like pop(), but returns the entire BagNode instead of just its value.
     *
     * @param {string} path - Hierarchical path to the node to remove.
     * @param {string|null} [reason=null] - Reason for deletion (for events).
     * @returns {BagNode|null} The removed BagNode, or null if not found.
     */
    popNode(path, reason = null) {
      const [obj, label] = this._htraverse(path, false, true);
      if (!obj || !label) return null;
      const node = obj._nodes.get(label);
      if (!node) return null;
      try {
        return obj._pop(label, reason);
      } finally {
        if (node.parentBag === obj && obj._nodes._dict[node.label] !== node) {
          node.parentBag = null;
        }
      }
    }
    // -------------------------------------------------------------------------
    // clear
    // -------------------------------------------------------------------------
    /**
     * Remove all nodes from this Bag.
     *
     * Empties the Bag completely. In backref mode, triggers delete events
     * for all removed nodes.
     */
    clear() {
      const oldNodes = [...this._nodes];
      this._nodes.clear();
      if (this.backref) {
        this._onNodeDeleted(oldNodes, -1);
      }
      for (const node of oldNodes) {
        node.parentBag = null;
      }
    }
    // -------------------------------------------------------------------------
    // getNode
    // -------------------------------------------------------------------------
    /**
     * Get the BagNode at a path (not its value).
     *
     * @param {string|number|null} path - Hierarchical path like 'a.b.c', integer index, or null.
     * @param {boolean} [isStatic=true] - If true, don't trigger resolvers.
     * @param {boolean} [autocreate=false] - If true, create node if not found.
     * @param {*} [defaultValue=null] - Default value for autocreated node.
     * @returns {BagNode|null} The BagNode if found, null otherwise.
     */
    getNode(path, isStatic = true, autocreate = false, defaultValue = null) {
      if (path === null || path === void 0 || path === "") {
        return this.parentNode;
      }
      if (typeof path === "number") {
        return this._nodes.get(path);
      }
      if (typeof path === "string") {
        path = path.split("?", 1)[0];
      }
      const [obj, label] = this._htraverse(path, autocreate, isStatic);
      if (obj instanceof _Bag && label) {
        const node = obj._nodes.get(label);
        if (node) {
          return node;
        }
        if (autocreate) {
          obj._nodes.set(
            label,
            defaultValue,
            ">",
            null,
            obj,
            null,
            false,
            true,
            "autocreate"
          );
          return obj._nodes.get(label);
        }
      }
      return null;
    }
    // -------------------------------------------------------------------------
    // Backref system
    // -------------------------------------------------------------------------
    /**
     * Enable backref mode (tree-leaf model with parent references).
     *
     * @param {BagNode|null} [node=null] - The BagNode that contains this Bag.
     * @param {Bag|null} [parent=null] - The parent Bag.
     */
    setBackref(node = null, parent = null) {
      const alreadyEnabled = this._backref;
      this._backref = true;
      this._parent = parent;
      this._parentNode = node;
      if (alreadyEnabled) return;
      this._nodes._parentBag = this;
      for (const n of this) {
        n.parentBag = this;
      }
    }
    /**
     * Clear parent reference and disable backref.
     */
    delParentRef() {
      this._parent = null;
      this._parentNode = null;
      this._backref = false;
    }
    /**
     * Clear all backref assumptions recursively.
     */
    clearBackref() {
      if (this._backref) {
        this._backref = false;
        this._parent = null;
        this._parentNode = null;
        this._nodes._parentBag = null;
        for (const node of this) {
          node.parentBag = null;
          const value = node.getValue(true);
          if (value instanceof _Bag) {
            value.clearBackref();
          }
        }
      }
    }
    // -------------------------------------------------------------------------
    // Event triggers
    // -------------------------------------------------------------------------
    /**
     * Trigger for node change events.
     *
     * @param {BagNode} node - The changed node.
     * @param {string[]} pathlist - Path to the node.
     * @param {string} evt - Event type ('upd_value', 'upd_attrs', 'upd_value_attr').
     * @param {*} [oldvalue=null] - Previous value (for value changes).
     * @param {Object|null} [attrsDiff=null] - Attribute diff dict { name: { old, new } }
     *   (for attribute changes).
     * @param {string|null} [reason=null] - Reason for change.
     */
    _onNodeChanged(node, pathlist, evt, oldvalue = null, attrsDiff = null, reason = null) {
      for (const s of Object.values(this._updSubscribers)) {
        s({ node, pathlist, oldvalue, attrs_diff: attrsDiff, evt, reason });
      }
      if (this._parent && this._parentNode) {
        this._parent._onNodeChanged(
          node,
          [this._parentNode.label, ...pathlist],
          evt,
          oldvalue,
          attrsDiff,
          reason
        );
      }
    }
    /**
     * Trigger for node insert events.
     *
     * @param {BagNode} node - The inserted node.
     * @param {number} ind - Index where inserted.
     * @param {string[]|null} [pathlist=null] - Path to the node.
     * @param {string|null} [reason=null] - Reason for insertion.
     */
    _onNodeInserted(node, ind, pathlist = null, reason = null) {
      const parent = node.parentBag;
      const value = node.getValue(true);
      if (parent !== null && parent.backref && value instanceof _Bag) {
        value.setBackref(node, parent);
      }
      if (pathlist === null) {
        pathlist = [];
      }
      for (const s of Object.values(this._insSubscribers)) {
        s({ node, pathlist, ind, evt: "ins", reason });
      }
      if (this._parent && this._parentNode) {
        this._parent._onNodeInserted(
          node,
          ind,
          [this._parentNode.label, ...pathlist],
          reason
        );
      }
    }
    /**
     * Trigger for node delete events.
     *
     * @param {BagNode|BagNode[]} node - The deleted node(s).
     * @param {number} ind - Index where deleted (-1 for clear).
     * @param {string[]|null} [pathlist=null] - Path to the node.
     * @param {string|null} [reason=null] - Reason for deletion.
     */
    _onNodeDeleted(node, ind, pathlist = null, reason = null) {
      for (const s of Object.values(this._delSubscribers)) {
        s({ node, pathlist, ind, evt: "del", reason });
      }
      if (this._parent && this._parentNode) {
        if (pathlist === null) {
          pathlist = [];
        }
        this._parent._onNodeDeleted(
          node,
          ind,
          [this._parentNode.label, ...pathlist],
          reason
        );
      }
    }
    // -------------------------------------------------------------------------
    // Subscription
    // -------------------------------------------------------------------------
    /**
     * Internal subscribe helper.
     */
    _subscribe(subscriberId, subscribersDict, callback) {
      if (callback !== null && callback !== void 0) {
        subscribersDict[subscriberId] = callback;
      }
    }
    /**
     * Subscribe to bag events.
     *
     * @param {string} subscriberId - Unique identifier for this subscription.
     * @param {Object} options - Subscription options.
     * @param {Function} [options.update] - Callback for update events.
     * @param {Function} [options.insert] - Callback for insert events.
     * @param {Function} [options.delete] - Callback for delete events.
     * @param {Function} [options.any] - Callback for all events.
     */
    subscribe(subscriberId, { update = null, insert = null, delete: del = null, any = null } = {}) {
      if (!this.backref) {
        this.setBackref();
      }
      this._subscribe(subscriberId, this._updSubscribers, update || any);
      this._subscribe(subscriberId, this._insSubscribers, insert || any);
      this._subscribe(subscriberId, this._delSubscribers, del || any);
    }
    /**
     * Unsubscribe from bag events.
     *
     * @param {string} subscriberId - The subscription identifier to remove.
     * @param {Object} options - Unsubscription options.
     * @param {boolean} [options.update=false] - Remove update subscription.
     * @param {boolean} [options.insert=false] - Remove insert subscription.
     * @param {boolean} [options.delete=false] - Remove delete subscription.
     * @param {boolean} [options.any=false] - Remove all subscriptions.
     */
    unsubscribe(subscriberId, { update = false, insert = false, delete: del = false, any = false } = {}) {
      if (update || any) {
        delete this._updSubscribers[subscriberId];
      }
      if (insert || any) {
        delete this._insSubscribers[subscriberId];
      }
      if (del || any) {
        delete this._delSubscribers[subscriberId];
      }
    }
    // -------------------------------------------------------------------------
    // Iteration
    // -------------------------------------------------------------------------
    /**
     * Iterate over BagNodes.
     */
    [Symbol.iterator]() {
      return this._nodes[Symbol.iterator]();
    }
    /**
     * Return node labels in order.
     *
     * @returns {string[]} Array of labels.
     */
    keys() {
      return this._nodes.keys();
    }
    /**
     * Return node values in order.
     *
     * @returns {Array} Array of values.
     */
    values() {
      return this._nodes.values();
    }
    /**
     * Return key/value objects in node order, resolving values as needed.
     *
     * @returns {Array<{key: string, value: *}>} Array of key/value objects.
     */
    items() {
      return [...this._nodes].map((node) => ({ key: node.label, value: node.getValue() }));
    }
    // -------------------------------------------------------------------------
    // Node Access Methods
    // -------------------------------------------------------------------------
    /**
     * Property alias for getNodes().
     *
     * @returns {BagNode[]} List of BagNodes.
     */
    get nodes() {
      return this.getNodes();
    }
    /**
     * Get a first-level node by label or index.
     *
     * Sync method for quick access to direct child nodes.
     * Does not traverse paths or trigger resolvers.
     *
     * @param {string|number} key - Node label (str) or index (int).
     * @returns {BagNode|null} The BagNode if found, null otherwise.
     *
     * @example
     * bag.node('a').value  // 1
     * bag.node(0).label    // 'a'
     */
    node(key) {
      return this._nodes.get(key);
    }
    /**
     * Set attributes on a node at the given path.
     *
     * @param {string|null} [path=null] - Path to the node.
     * @param {Object|null} [attr=null] - Dict of attributes to set.
     * @param {boolean} [removeNullAttributes=true] - If true, remove attributes with null value.
     */
    setAttr(path = null, attr = null, removeNullAttributes = true) {
      const node = _Bag.prototype.getNode.call(this, path, true, true);
      if (node) {
        node.setAttr(attr, true, true, removeNullAttributes);
      }
    }
    /**
     * Get an attribute from a node at the given path.
     *
     * @param {string|null} [path=null] - Path to the node.
     * @param {string|null} [attr=null] - Attribute name to get.
     * @param {*} [defaultVal=null] - Default value if node or attribute not found.
     * @returns {*} Attribute value or default.
     */
    getAttr(path = null, attr = null, defaultVal = null) {
      const node = this.getNode(path);
      if (node) {
        return node.getAttr(attr, defaultVal);
      }
      return defaultVal;
    }
    /**
     * Delete attributes from a node at the given path.
     *
     * @param {string|null} [path=null] - Path to the node.
     * @param {...string} attrs - Attribute names to delete.
     */
    delAttr(path = null, ...attrs) {
      const node = this.getNode(path);
      if (node) {
        node.delAttr(...attrs);
      }
    }
    /**
     * Get inherited attributes from parent chain.
     *
     * @returns {Object} Dict of attributes inherited from parent nodes.
     */
    getInheritedAttributes() {
      if (this._parentNode) {
        return this._parentNode.getInheritedAttributes();
      }
      return {};
    }
    // -------------------------------------------------------------------------
    // Query Methods (BagQuery)
    // -------------------------------------------------------------------------
    /**
     * Get the actual list of nodes contained in the Bag.
     *
     * The getNodes method works as the filter of a list.
     *
     * @param {Function|null} [condition=null] - Optional callable that takes a BagNode and returns bool.
     * Returns a new list of shared nodes. List mutations do not change the Bag;
     * node mutations do. Later structural changes are not reflected in the list.
     * @returns {BagNode[]} Snapshot of BagNodes, optionally filtered by condition.
     */
    getNodes(condition = null) {
      if (!condition) {
        return [...this._nodes];
      }
      return [...this._nodes].filter((n) => condition(n));
    }
    /**
     * Return the first BagNode whose value contains key=value.
     *
     * Searches only direct children (not recursive).
     * The node's value must be dict-like (Bag or dict).
     *
     * @param {string} key - Key to look for in node.value.
     * @param {*} value - Value to match.
     * @returns {BagNode|null} BagNode if found, null otherwise.
     */
    getNodeByValue(key, value) {
      for (const node of this._nodes) {
        const nodeValue = node.value;
        if (nodeValue instanceof _Bag) {
          if (nodeValue.getItem(key) === value) return node;
        } else if (nodeValue && nodeValue.get && nodeValue.get(key) === value) {
          return node;
        }
      }
      return null;
    }
    /**
     * Return the first BagNode with the requested attribute value.
     *
     * Search strategy (hybrid depth-first with level priority):
     * 1. First checks all direct children of current Bag
     * 2. Then recursively searches into sub-Bags (depth-first)
     *
     * This means a match at the current level is always found before
     * descending into nested Bags, but once descent begins, it proceeds
     * depth-first through the subtree before checking siblings.
     *
     * @param {string} attr - Attribute name to search.
     * @param {*} value - Attribute value; undefined searches for presence.
     * @param {boolean} [caseInsensitive=false] - Compare strings ignoring case.
     * @param {boolean} [deep_first=false] - Visit subtrees before next siblings.
     * @returns {BagNode|null} BagNode if found, null otherwise.
     */
    getNodeByAttr(attr, value, caseInsensitive = false, deep_first = false) {
      const existsOnly = value === void 0;
      const expected = caseInsensitive && typeof value === "string" ? value.toLowerCase() : value;
      const search = (bag) => {
        const subBags = [];
        for (const node of bag._nodes) {
          if (attr in node.attr) {
            const current = caseInsensitive && typeof node.attr[attr] === "string" ? node.attr[attr].toLowerCase() : node.attr[attr];
            if (existsOnly || current == expected) return node;
          }
          if (node._value instanceof _Bag) {
            if (deep_first) {
              const found = search(node._value);
              if (found) return found;
            } else {
              subBags.push(node._value);
            }
          }
        }
        for (const child of subBags) {
          const found = search(child);
          if (found) return found;
        }
        return null;
      };
      return search(this);
    }
    /**
     * Check if the Bag is empty.
     *
     * A node is considered non-empty if:
     * - It has a resolver (even if static value is null, the resolver
     *   represents potential content that can be loaded)
     * - It has a non-null static value (unless zeroIsNone/blankIsNone apply)
     *
     * This method never triggers resolver I/O - it only checks static values
     * and resolver presence.
     *
     * @param {boolean} [zeroIsNone=false] - If true, treat 0 values as empty.
     * @param {boolean} [blankIsNone=false] - If true, treat blank strings as empty.
     * @returns {boolean} True if Bag is empty according to criteria, false otherwise.
     */
    isEmpty(zeroIsNone = false, blankIsNone = false) {
      if (this._nodes.length === 0) {
        return true;
      }
      for (const node of this._nodes) {
        if (node._resolver !== null) {
          return false;
        }
        const v = node.getValue(true);
        if (v === null || v === void 0) {
          continue;
        }
        if (zeroIsNone && v === 0) {
          continue;
        }
        if (blankIsNone && v === "") {
          continue;
        }
        return false;
      }
      return true;
    }
    /**
     * Query Bag elements, extracting specified data.
     *
     * @param {string|Array|null} [what=null] - String of special keys separated by comma, or array of keys.
     *     Special keys:
     *     - '#k': label of each item
     *     - '#v': value of each item
     *     - '#v.path': inner values of each item
     *     - '#__v': static value (always bypasses resolver)
     *     - '#a': all attributes of each item
     *     - '#a.attrname': specific attribute for each item
     *     - '#p': path (full path from root, useful with deep=true)
     *     - '#n': node (the BagNode itself)
     *     - callable: custom function applied to each node
     * @param {Function|boolean|null} [condition=null] - Optional callable filter (receives BagNode, returns bool).
     * A boolean is the deprecated legacy asColumns argument and emits a warning.
     * @param {boolean} [iter=false] - If true, return a generator instead of an array.
     * @param {boolean} [deep=false] - If true, traverse recursively (depth-first) instead of first level only.
     * @param {boolean} [leaf=true] - If true (default), include leaf nodes (non-Bag values).
     * @param {boolean} [branch=true] - If true (default), include branch nodes (Bag values).
     * @param {number|null} [limit=null] - Maximum number of results to return. null means no limit.
     * @param {boolean} [isStatic=true] - If true (default), don't trigger resolvers during traversal.
     * @returns {Array|Generator} Array of tuples, or generator if iter=true.
     */
    query(what = null, condition = null, iter = false, deep = false, leaf = true, branch = true, limit = null, isStatic = true) {
      if (!what) {
        what = "#k,#v,#a";
      }
      let obj = this;
      let whatsplit;
      if (typeof what === "string") {
        if (what.includes(":")) {
          const [where, whatPart] = what.split(":");
          obj = this.getItem(where);
          what = whatPart;
        }
        whatsplit = what.split(",").map((x) => x.trim());
      } else {
        whatsplit = what;
      }
      const _extractValue = (node, w, path, isDeep, readValue) => {
        if (w === "#k") {
          return node.label;
        } else if (w === "#p") {
          return path;
        } else if (w === "#n") {
          return node;
        } else if (typeof w === "function") {
          return w(node);
        } else if (w === "#v") {
          const v = readValue();
          return isDeep && v instanceof _Bag ? null : v;
        } else if (w.startsWith("#v.")) {
          const innerPath = w.split(".").slice(1).join(".");
          const value = readValue();
          return value && value.getItem ? value.getItem(innerPath) : null;
        } else if (w === "#__v") {
          return node.getValue(true);
        } else if (w.startsWith("#a")) {
          const attr = w.includes(".") ? w.split(".").slice(1).join(".") : null;
          return node.getAttr(attr);
        } else {
          const value = readValue();
          return value && value.getItem ? value.getItem(w) : null;
        }
      };
      function* _iterDigest() {
        let count = 0;
        function* visit(bag, prefix) {
          for (const node of bag._nodes) {
            const path = prefix ? `${prefix}.${node.label}` : node.label;
            let loaded = false;
            let value;
            const readValue = () => {
              if (!loaded) {
                value = node.getValue(isStatic);
                loaded = true;
              }
              return value;
            };
            const included = leaf && branch || (readValue() instanceof _Bag ? branch : leaf);
            if (included && (condition === null || condition(node))) {
              yield whatsplit.length === 1 ? _extractValue(node, whatsplit[0], path, deep, readValue) : whatsplit.map((w) => _extractValue(node, w, path, deep, readValue));
              count++;
              if (limit !== null && count >= limit) return;
            }
            if (deep) {
              const child = readValue();
              if (child instanceof _Bag) {
                yield* visit(child, path);
                if (limit !== null && count >= limit) return;
              }
            }
          }
        }
        yield* visit(obj, "");
      }
      if (iter) {
        return _iterDigest();
      }
      return [..._iterDigest()];
    }
    /**
     * Return [relative path, value] pairs for non-Bag leaves.
     * Resolve each node once per occurrence. Empty Bags produce no leaf entry.
     * Paths do not require parent backrefs.
     */
    getLeaves() {
      const result = [];
      const collect = (bag, prefix) => {
        for (const node of bag._nodes) {
          const path = prefix ? `${prefix}.${node.label}` : node.label;
          const value = node.getValue(false);
          if (value instanceof _Bag) collect(value, path);
          else result.push([path, value]);
        }
      };
      collect(this, "");
      return result;
    }
    /**
     * Return a list of tuples with keys/values/attributes (backward compatible).
     *
     * This is an alias for query() with iter=false, deep=false for backward
     * compatibility. Use query() for new code.
     *
     * @param {string|Array|null} [what=null] - String of special keys separated by comma, or array of keys.
     * @param {Function|boolean|null} [condition=null] - Optional callable filter (receives BagNode, returns bool).
     * A boolean is the deprecated legacy asColumns argument and emits a warning.
     * @param {boolean} [asColumns=false] - If true, return array of arrays (transposed).
     * @returns {Array} Array of tuples (or array of arrays if asColumns=true).
     */
    digest(what = null, condition = null, asColumns = false) {
      if (typeof condition === "boolean") {
        console.warn("Bag.digest(what, asColumns) is deprecated; use digest(what, null, asColumns).");
        asColumns = condition;
        condition = null;
      }
      const result = this.query(what, condition, false, false, true, true, null, false);
      if (asColumns) {
        if (!result || result.length === 0) {
          const whatStr = typeof what === "string" ? what : "#k,#v,#a";
          const whatsplit = whatStr.split(",").map((x) => x.trim());
          return whatsplit.map(() => []);
        }
        const resultList = [...result];
        if (resultList.length && Array.isArray(resultList[0])) {
          const numCols = resultList[0].length;
          const columns = [];
          for (let i = 0; i < numCols; i++) {
            columns.push(resultList.map((row) => row[i]));
          }
          return columns;
        }
        return [resultList];
      }
      return [...result];
    }
    /**
     * Return digest result as columns.
     *
     * @param {string|Array} cols - Column names as comma-separated string or array.
     * @param {boolean} [attrMode=false] - If true, prefix columns with '#a.' for attribute access.
     * @returns {Array} Array of arrays (columns).
     */
    columns(cols, attrMode = false) {
      if (typeof cols === "string") {
        cols = cols.split(",");
      }
      const mode = attrMode ? "#a." : "";
      const what = cols.map((col) => `${mode}${col}`).join(",");
      return this.digest(what, null, true);
    }
    /**
     * Sum selected values at the current level; never traverse recursively.
     * @param {string} [what='#v'] - Query criterion, or comma-separated criteria.
     * @param {boolean} [strict=false] - Return null for null/undefined/empty string.
     * Otherwise these values contribute zero. Non-numeric values are ignored
     * unless strict, which raises TypeError. Zero and false remain valid.
     * @param {Function|null} [condition=null] - Optional BagNode predicate.
     * @returns {number|null|Array} One result, or one result per criterion.
     */
    sum(what = "#v", strict = false, condition = null) {
      if (strict != null && typeof strict !== "boolean") {
        throw new TypeError("sum strict must be a boolean; pass condition as the third argument");
      }
      if (condition != null && typeof condition !== "function") {
        throw new TypeError("sum condition must be callable; deep is no longer supported");
      }
      const total = (criterion) => {
        let result = 0;
        let missing = false;
        for (const value of this.query(criterion, condition)) {
          if (value == null || value === "") {
            missing = true;
            continue;
          }
          if (typeof value !== "number" && typeof value !== "boolean") {
            if (strict) throw new TypeError(`sum encountered non-numeric value: ${typeof value}`);
            continue;
          }
          result += value;
        }
        return strict && missing ? null : result;
      };
      return what.includes(",") ? what.split(",").map((w) => total(w.trim())) : total(what);
    }
    /**
     * Sort nodes in place.
     *
     * @param {string|Function} [key='#k:a'] - Sort specification string or callable.
     *     If callable, used directly as key function for sort.
     *     If string, format is 'criterion:mode' or multiple 'c1:m1,c2:m2'.
     *
     *     Criteria:
     *     - '#k': sort by label
     *     - '#v': sort by value
     *     - '#a.attrname': sort by attribute
     *     - 'fieldname': sort by field in value (if value is dict/Bag)
     *
     *     Modes:
     *     - 'a': ascending, case-insensitive (default)
     *     - 'A': ascending, case-sensitive
     *     - 'd': descending, case-insensitive
     *     - 'D': descending, case-sensitive
     *
     * @returns {Bag} Self (for chaining).
     *
     * @example
     * bag.sort('#k')           // by label ascending
     * bag.sort('#k:d')         // by label descending
     * bag.sort('#v:A')         // by value ascending, case-sensitive
     * bag.sort('#a.name:a')    // by attribute 'name'
     * bag.sort('field:d')      // by field in value
     * bag.sort('#k:a,#v:d')    // multi-level sort
     * bag.sort(n => n.value)   // custom key function
     */
    sort(key = "#k:a") {
      const sortKey = (value, caseInsensitive) => {
        if (value === null || value === void 0) {
          return [-1, ""];
        }
        if (caseInsensitive && typeof value === "string") {
          return [0, value.toLowerCase()];
        }
        return [0, value];
      };
      const compareKeys = (a, b) => {
        if (a[0] !== b[0]) {
          return a[0] - b[0];
        }
        if (a[1] < b[1]) return -1;
        if (a[1] > b[1]) return 1;
        return 0;
      };
      if (typeof key === "function") {
        this._nodes._list.sort((a, b) => {
          const ka = key(a);
          const kb = key(b);
          if (ka < kb) return -1;
          if (ka > kb) return 1;
          return 0;
        });
      } else {
        const levels = key.split(",");
        levels.reverse();
        for (const level of levels) {
          let what, mode;
          if (level.includes(":")) {
            [what, mode] = level.split(":", 2);
          } else {
            what = level;
            mode = "a";
          }
          what = what.trim();
          mode = mode.trim();
          const reverse = mode === "d" || mode === "D";
          const caseInsensitive = mode === "a" || mode === "d";
          let keyFn;
          if (what.toLowerCase() === "#k") {
            keyFn = (n) => sortKey(n.label, caseInsensitive);
          } else if (what.toLowerCase() === "#v") {
            keyFn = (n) => sortKey(n.value, caseInsensitive);
          } else if (what.toLowerCase().startsWith("#a.")) {
            const attrname = what.slice(3);
            keyFn = (n) => sortKey(n.getAttr(attrname), caseInsensitive);
          } else {
            keyFn = (n) => {
              const value = n.value;
              const field = value instanceof _Bag ? value.getItem(what) : value ? value[what] : null;
              return sortKey(field, caseInsensitive);
            };
          }
          this._nodes._list.sort((a, b) => {
            const result = compareKeys(keyFn(a), keyFn(b));
            return reverse ? -result : result;
          });
        }
      }
      return this;
    }
    /**
     * Check equality with another Bag.
     *
     * @param {Bag} other - Bag to compare with.
     * @returns {boolean} True if both Bags have same nodes with same values and attributes.
     */
    equalTo(other) {
      if (!(other instanceof _Bag)) return false;
      return this._nodes.isEqual(other._nodes);
    }
    /**
     * Check if a path or node exists in the Bag.
     *
     * Equivalent to Python's `__contains__` / `in` operator.
     *
     * With the `?attr` query syntax it checks the existence of the named
     * attribute on the target node; `?a&b` requires every named attribute
     * to be present. The check is static: it does not trigger resolvers
     * along the path.
     *
     * @param {string|BagNode} what - Path to check, optionally with a
     *   `?attr` or `?a&b` suffix, or a BagNode to check if it's in this Bag.
     * @returns {boolean} True if the path/node (and named attributes if
     *   provided) exists, false otherwise.
     *
     * @example
     * bag.setItem('a.b', 1);
     * bag.has('a.b')          // true
     * bag.has('a.c')          // false
     * bag.has('a.b?color')    // true if node a.b has attribute 'color'
     * bag.has('a.b?x&y')      // true only if both 'x' and 'y' are present
     */
    has(what) {
      if (typeof what === "string") {
        let queryString = null;
        if (what.includes("?")) {
          [what, queryString] = what.split("?", 2);
        }
        const node = this.getNode(what);
        if (node === null) {
          return false;
        }
        if (queryString === null) {
          return true;
        }
        return queryString.split("&").every((a) => a in node.attr);
      } else if (what && what.label !== void 0) {
        return [...this._nodes].includes(what);
      }
      return false;
    }
    // -------------------------------------------------------------------------
    // Resolver Methods
    // -------------------------------------------------------------------------
    /**
     * Get the resolver at the given path.
     *
     * @param {string} path - Path to the node.
     * @returns {*} The resolver, or null if path doesn't exist or has no resolver.
     */
    getResolver(path) {
      const node = this.getNode(path);
      return node ? node.resolver : null;
    }
    /**
     * Set a resolver at the given path.
     *
     * Creates the node if it doesn't exist, with value=null.
     *
     * @param {string} path - Path to the node.
     * @param {*} resolver - The resolver to set.
     */
    setResolver(path, resolver) {
      let node = this.getNode(path);
      if (!node) {
        this.setItem(path, null);
        node = this.getNode(path);
      }
      node.resolver = resolver;
    }
    /**
     * Set a callback resolver at the given path.
     *
     * Shortcut for creating a BagCbResolver and setting it on a node.
     *
     * @param {string} path - Path to the node.
     * @param {Function} callback - Callable that returns the value.
     * @param {Object} [options={}] - Options passed to BagCbResolver constructor.
     *     - cacheTime: Cache duration in ms (default 0, no cache).
     *     - readOnly: If true, value not saved in node (default false).
     */
    setCallbackItem(path, callback, options = {}) {
      const resolver = new BagCbResolver({ callback, ...options });
      this.setResolver(path, resolver);
    }
    // -------------------------------------------------------------------------
    // Structure Manipulation Methods
    // -------------------------------------------------------------------------
    /**
     * Move element(s) to a new position.
     *
     * @param {number|number[]} what - Index or list of indices to move.
     * @param {number} position - Target index position.
     * @param {boolean} [trigger=true] - If true, fire del/ins events.
     *
     * @example
     * bag.move(0, 2)      // move first element to position 2
     * bag.move([0, 2], 1) // move indices 0 and 2 to position 1
     */
    move(what, position, trigger = true) {
      this._nodes.move(what, position, trigger);
    }
    /**
     * Convert Bag to plain object (first level only).
     *
     * @param {boolean} [ascii=false] - If true, convert keys to ASCII.
     * @param {boolean} [lower=false] - If true, convert keys to lowercase.
     * @param {boolean} [recursive=false] - Convert nested Bags (not ordinary objects/arrays).
     * @param {boolean} [excludeNullValues=false] - Omit null/undefined, retaining empty Bags.
     * @returns {Object} Plain JavaScript object with key-value pairs.
     */
    asDict(ascii = false, lower = false, recursive = false, excludeNullValues = false) {
      const result = {};
      for (const el of this._nodes) {
        let value = el.value;
        if (excludeNullValues && value == null) continue;
        let key = el.label;
        if (ascii) {
          key = String(key);
        }
        if (lower) {
          key = key.toLowerCase();
        }
        if (recursive && value instanceof _Bag) {
          value = _Bag.prototype.asDict.call(value, ascii, lower, recursive, excludeNullValues);
        }
        Object.defineProperty(result, key, {
          value,
          enumerable: true,
          writable: true,
          configurable: true
        });
      }
      return result;
    }
    /**
     * Return value at path, setting it to default if not present.
     *
     * @param {string} path - Path to the value.
     * @param {*} [defaultVal=null] - Default value to set if path doesn't exist.
     * @returns {*} The value at path (existing or newly set default).
     */
    setdefault(path, defaultVal = null) {
      const node = this.getNode(path);
      if (!node) {
        this.setItem(path, defaultVal);
        return defaultVal;
      }
      return node.value;
    }
    /**
     * Return a deep copy of this Bag.
     *
     * Creates a new Bag with copies of all nodes. Nested Bags are
     * recursively deep copied. Values are copied by reference unless
     * they are Bags. Node attributes are copied as a new dict.
     *
     * @param {boolean} [resolve=false] - Resolve values before copying.
     * @returns {Bag} A new Bag with copied nodes.
     *
     * @example
     * const copy = bag.deepcopy();
     * copy.setItem('b.c', 3);
     * // Original bag['b.c'] unchanged
     */
    deepcopy(resolve = false) {
      const result = this.createChildBag();
      for (const node of this._nodes) {
        let value = node.getValue(!resolve);
        if (value instanceof _Bag) value = value.deepcopy(resolve);
        const copied = new result.nodeClass(result, node.label, value);
        copied.setAttr({ ...node.attr }, false, false, false);
        copied.nodeTag = node.nodeTag;
        copied.xmlTag = node.xmlTag;
        result._nodes._list.push(copied);
        result._nodes._dict[copied.label] = copied;
      }
      return result;
    }
    /**
     * Merge a Bag or object using the legacy JavaScript argument order.
     *
     * @param {Bag|Object} source - Incoming nodes or key/value properties.
     * @param {string|null} [mode=null] - 'static' preserves source resolvers;
     * otherwise their values are resolved before copying.
     * @param {*} [reason=null] - Modification reason passed to subscribers.
     * @param {boolean} [ignoreNone=false] - Optional extension: preserve existing
     * values when the incoming value is null. It is not the mode argument.
     */
    update(source, mode = null, reason = null, ignoreNone = false) {
      if (!(source instanceof _Bag)) {
        for (const label in source) {
          const value = source[label];
          if (!ignoreNone || value !== null || !this._nodes.has(label)) {
            this.setItem(
              label,
              value,
              null,
              ">",
              false,
              false,
              reason,
              false,
              reason !== false
            );
          }
        }
        return;
      }
      for (const incoming of [...source]) {
        const label = incoming.label;
        const resolver = mode === "static" ? incoming.resolver : null;
        const value = resolver ? null : incoming.getValue();
        const replaceContent = incoming.attr.__replace;
        delete incoming.attr.__replace;
        const current = this._nodes.get(label);
        if (current) {
          current.setAttr(incoming.attr, reason === null ? true : reason, true, false);
          if (incoming.nodeTag != null) current.nodeTag = incoming.nodeTag;
          if (incoming.xmlTag != null) current.xmlTag = incoming.xmlTag;
          if (resolver) {
            current.resolver = resolver;
            current.setValue(
              null,
              reason === null ? true : reason,
              null,
              null,
              false,
              reason
            );
          } else {
            if (incoming.resolver) current.resolver = null;
            const previous = current.getValue();
            if (value instanceof _Bag && previous instanceof _Bag && !replaceContent) {
              previous.update(value, mode, reason, ignoreNone);
            } else if (!ignoreNone || value !== null) {
              current.setValue(
                value,
                reason === null ? true : reason,
                null,
                null,
                false,
                reason
              );
            }
          }
        } else {
          const node = this.setItem(
            label,
            resolver || value,
            incoming.attr,
            ">",
            false,
            false,
            reason,
            false,
            reason !== false
          );
          node.nodeTag = incoming.nodeTag;
          node.xmlTag = incoming.xmlTag;
        }
      }
    }
    // -------------------------------------------------------------------------
    // Construction and Filling Methods
    // -------------------------------------------------------------------------
    /**
     * Copy nodes from another Bag.
     *
     * Clears current contents and copies all nodes from the source Bag.
     * Nested Bags are deep copied.
     *
     * @param {Bag} other - Source Bag to copy from.
     * @private
     */
    _fillFromBag(other) {
      this.clear();
      for (const node of other) {
        const copied = new this.nodeClass(this, node.label);
        copied.replace(node);
        copied.nodeTag = node.nodeTag;
        copied.xmlTag = node.xmlTag;
        this._nodes._list.push(copied);
        this._nodes._dict[copied.label] = copied;
      }
    }
    /**
     * Populate bag from a plain object (dictionary).
     *
     * Clears current contents and creates nodes from object properties.
     * Nested objects are converted to nested Bags.
     *
     * @param {Object} data - Object where keys become labels and values become node values.
     * @private
     */
    _fillFromDict(data) {
      this.clear();
      for (const [key, value] of Object.entries(data)) {
        if (value !== null && typeof value === "object" && !Array.isArray(value) && !(value instanceof _Bag) && !(value instanceof BagNode)) {
          this.setItem(key, this.createChildBag()._loadSource(value));
        } else {
          this.setItem(key, value);
        }
      }
    }
    /**
     * Fill this Bag from a source (another Bag or plain object).
     *
     * Prepares replacement contents before changing this Bag:
     * - If source is null/undefined: no-op
     * - If source is a Bag: copies all nodes (deep copy for nested Bags)
     * - If source is a plain object: keys become labels, values become node values.
     *   Nested objects are recursively converted to Bags.
     *
     * Preparation errors leave this Bag unchanged. Attached Bags emit one
     * upd_value event after replacement, carrying the previous content.
     * Listener exceptions propagate after the replacement has committed.
     *
     * @param {Bag|Object|null} source - Source to fill from.
     * @returns {Bag} This Bag (for chaining).
     *
     * @example
     * const bag = new Bag();
     * bag.replace(new Bag({ a: 1, b: { c: 2 } }));
     * // bag has 'a' = 1, 'b' = Bag with 'c' = 2
     *
     * const other = new Bag();
     * other.setItem('x', 10);
     * bag.replace(other);
     * // bag now has only 'x' = 10
     */
    _loadSource(source) {
      if (source == null) return this;
      const prepared = this.createChildBag();
      if (source instanceof _Bag) {
        prepared._fillFromBag(source);
      } else if (typeof source === "object" && !Array.isArray(source)) {
        prepared._fillFromDict(source);
      } else {
        return this;
      }
      return this._replacePrepared(prepared);
    }
    /** Replace all contents from a Bag, preserving identity. Returns this. */
    replace(other) {
      if (!(other instanceof _Bag)) throw new TypeError("Bag.replace expects a Bag");
      if (other === this) return this;
      const prepared = this.createChildBag();
      prepared._fillFromBag(other);
      return this._replacePrepared(prepared);
    }
    _replacePrepared(prepared) {
      for (const node of this._nodes) {
        node.parentBag = null;
        const value = node.getValue(true);
        if (value instanceof _Bag) value.clearBackref();
      }
      const oldNodes = this._nodes;
      this._nodes = prepared._nodes;
      prepared._nodes = oldNodes;
      this._nodes._parentBag = this.backref ? this : null;
      prepared._nodes._parentBag = null;
      for (const node of this._nodes) node.parentBag = this;
      for (const node of prepared._nodes) node._parentBag = prepared;
      if (this.backref && this.parent && this.parentNode) {
        this.parent._onNodeChanged(
          this.parentNode,
          [this.parentNode.label],
          "upd_value",
          prepared
        );
      }
      return this;
    }
    /**
     * Visit direct nodes, or the full tree with deep=true.
     * Null/undefined descends; falsey non-null results skip children;
     * a truthy result stops the visit and is returned.
     * Callback receives (node, kwargs, siblingIndex).
     */
    forEach(callback, { static: isStatic = true, deep = false, kwargs = {} } = {}) {
      if (typeof callback !== "function") throw new TypeError("forEach requires a callback");
      const visit = (bag, context) => {
        for (let index = 0; index < bag._nodes.length; index++) {
          const node = bag._nodes._list[index];
          const kw = { ...context };
          if ("_pathlist" in context) kw._pathlist = [...context._pathlist, node.label];
          if ("_indexlist" in context) kw._indexlist = [...context._indexlist, index];
          const result = callback(node, kw, index);
          if (result) return result;
          if (result == null && deep) {
            const value = node.getValue(isStatic);
            if (value instanceof _Bag) {
              const innerResult = visit(value, kw);
              if (innerResult) return innerResult;
            }
          }
        }
        return null;
      };
      return visit(this, kwargs);
    }
    /**
     * Yield original nodes depth-first, parent before children.
     * Values are read statically: lazy resolvers are not invoked.
     * Shared subtrees are visited at each path, as in legacy Python.
     * @yields {BagNode}
     */
    *traverse() {
      for (const node of this._nodes) {
        yield node;
        const value = node.getValue(true);
        if (value instanceof _Bag) {
          yield* value.traverse();
        }
      }
    }
    /** Stream path/node pairs for internal query and serialization use. */
    *_iterNodesWithPaths(isStatic = true, prefix = "") {
      for (const node of this._nodes) {
        const path = prefix ? `${prefix}.${node.label}` : node.label;
        yield [path, node];
        const value = node.getValue(isStatic);
        if (value instanceof _Bag) yield* value._iterNodesWithPaths(isStatic, path);
      }
    }
    // -------------------------------------------------------------------------
    // TyTx Serialization
    // -------------------------------------------------------------------------
    /**
     * Flatten nodes into (parent, label, tag, value, attr) tuples for TyTx.
     *
     * @param {Object|null} [pathRegistry=null] - If provided, enable compact mode.
     * @yields {Array} Tuples of [parent, label, tag, value, attr].
     */
    *_nodeFlattener(pathRegistry = null) {
      const compact = pathRegistry !== null;
      const pathToCode = compact ? /* @__PURE__ */ Object.create(null) : null;
      let codeCounter = 0;
      for (const [path, node] of serializationNodes(this)) {
        const lastDot = path.lastIndexOf(".");
        const parentPath = lastDot >= 0 ? path.slice(0, lastDot) : "";
        const nodeValue = node.getValue(true);
        let value;
        if (node.resolver) {
          value = encodeResolver(node.resolver);
        } else if (nodeValue instanceof _Bag) {
          const cls = nodeValue.constructor;
          const suffix = cls.tytxSuffix;
          const registered = getRegisteredType(suffix);
          if (registered !== cls && !(suffix === "X" && registered === _Bag)) {
            throw new BagSerializationError(`Unregistered Bag branch type: ${cls.name}`);
          }
          value = `::${suffix}`;
        } else if (nodeValue === null) {
          value = "::NN";
        } else {
          value = nodeValue;
        }
        const attr = encodeAttrs(node.attr);
        const tag = node.nodeTag;
        if (compact) {
          const parentRef = parentPath ? pathToCode[parentPath] : null;
          yield [parentRef, node.label, tag, value, attr];
          if (nodeValue instanceof _Bag) {
            pathToCode[path] = codeCounter;
            pathRegistry[codeCounter] = path;
            codeCounter++;
          }
        } else {
          yield [parentPath, node.label, tag, value, attr];
        }
      }
    }
    /**
     * Serialize Bag to TyTx format.
     *
     * Converts the Bag hierarchy into a flat list of row tuples,
     * then encodes using TyTx which preserves types (Decimal, Date, etc.).
     *
     * @param {string} [transport='json'] - Output format: 'json' or 'msgpack'.
     * @param {boolean} [compact=false] - If true, use numeric path codes.
     * @returns {string|Uint8Array} Serialized data.
     */
    toTytx(transport = "json", compact = false) {
      let data;
      if (compact) {
        const paths = {};
        const rows = [...this._nodeFlattener(paths)];
        data = { rows, paths };
      } else {
        const rows = [...this._nodeFlattener(null)];
        data = { rows };
      }
      const tytxTransport = transport === "json" ? null : transport;
      return toTytx(data, tytxTransport);
    }
    /**
     * Deserialize Bag from TyTx format.
     *
     * @param {string|Uint8Array} data - Serialized data from toTytx().
     * @param {string} [transport='json'] - Input format: 'json' or 'msgpack'.
     * @returns {Bag} Reconstructed Bag.
     */
    static fromTytx(data, transport = "json") {
      if (data === "") return new this();
      const parsed = fromTytx(data, transport === "json" ? null : transport);
      if (!parsed || !Array.isArray(parsed.rows)) {
        throw new BagSerializationError("Invalid TYTX Bag: expected rows");
      }
      const paths = parsed.paths;
      const compact = paths != null;
      const bag = new this();
      const pathToBag = /* @__PURE__ */ new Map([["", bag]]);
      for (const row of parsed.rows) {
        if (!Array.isArray(row) || row.length !== 5) {
          throw new BagSerializationError("Invalid TYTX Bag row");
        }
        const [parentRef, label, tag, rawValue, rawAttr] = row;
        let parentPath = parentRef ?? "";
        if (compact) {
          if (parentRef !== null && !Object.hasOwn(paths, parentRef)) {
            throw new BagSerializationError(`Unknown TYTX parent reference: ${parentRef}`);
          }
          parentPath = parentRef === null ? "" : paths[parentRef];
        }
        if (!pathToBag.has(parentPath)) {
          throw new BagSerializationError(`Missing or undecodable TYTX parent branch: ${parentPath}`);
        }
        const parentBag = pathToBag.get(parentPath);
        const fullPath = parentPath ? `${parentPath}.${label}` : label;
        let value = rawValue;
        if (transport === "msgpack" && typeof value === "string" && value.startsWith("::")) {
          const cls = getRegisteredType(value.slice(2));
          if (cls === _Bag || cls?.prototype instanceof _Bag) value = fromTytx(value);
        }
        const resolver = decodeResolver(value);
        if (value instanceof _Bag) {
          let cls = value.constructor;
          if (cls.tytxSuffix === "X" && this.tytxSuffix === "X") cls = this;
          value = new cls();
          pathToBag.set(fullPath, value);
        } else if (value === "::NN") {
          value = null;
        }
        const node = parentBag.setItem(label, resolver || value, decodeAttrs(rawAttr));
        node.nodeTag = tag ?? null;
      }
      return bag;
    }
    // -------------------------------------------------------------------------
    // XML Serialization
    // -------------------------------------------------------------------------
    /**
     * Serialize Bag to XML format.
     *
     * All values are converted to strings without type information.
     * For type-preserving serialization, use toTytx() instead.
     *
     * @param {Object} [options={}] - Serialization options.
     * @param {boolean} [options.pretty=false] - If true, format with indentation.
     * @param {string} [options.encoding='UTF-8'] - XML encoding.
     * @param {boolean|string} [options.docHeader=null] - XML declaration.
     * @param {string[]} [options.selfClosedTags=null] - Tags to self-close when empty.
     * @returns {string} XML string.
     */
    toXml(options = {}) {
      const { pretty = false, encoding = "UTF-8", docHeader = null, selfClosedTags = null } = options;
      let content = this._bagToXml(selfClosedTags, pretty);
      if (docHeader === true) {
        content = `<?xml version='1.0' encoding='${encoding}'?>
${content}`;
      } else if (typeof docHeader === "string") {
        content = `${docHeader}
${content}`;
      }
      return content;
    }
    /**
     * Convert Bag to XML string (internal).
     * @private
     */
    _bagToXml(selfClosedTags = null, pretty = false, depth = 0) {
      const parts = [];
      for (const node of this._nodes) {
        parts.push((pretty ? "  ".repeat(depth) : "") + this._nodeToXml(node, selfClosedTags, pretty, depth));
      }
      return parts.join(pretty ? "\n" : "");
    }
    /**
     * Convert a BagNode to XML string (internal).
     * @private
     */
    _nodeToXml(node, selfClosedTags = null, pretty = false, depth = 0) {
      const originalTag = node.xmlTag || node.nodeTag || node.label;
      const tag = this._sanitizeTag(originalTag);
      const attrsParts = [];
      if (tag !== originalTag) {
        attrsParts.push(`_tag="${this._escapeAttr(originalTag)}"`);
      }
      if (node.resolver) {
        attrsParts.push(`_resolver="${this._escapeAttr(encodeResolver(node.resolver))}"`);
      }
      if (node.attr) {
        for (const [k, v] of Object.entries(encodeAttrs(node.attr))) {
          if (v !== null && v !== false && v !== void 0) {
            attrsParts.push(`${k}="${this._escapeAttr(String(v))}"`);
          }
        }
      }
      const attrsStr = attrsParts.length ? " " + attrsParts.join(" ") : "";
      const value = node.resolver ? null : node.getValue(true);
      if (value && typeof value._bagToXml === "function") {
        pretty = pretty && node.attr?.["xml:space"] !== "preserve";
        const inner = value._bagToXml(selfClosedTags, pretty, depth + 1);
        if (inner) {
          if (pretty) {
            return `<${tag}${attrsStr}>
${inner}
${"  ".repeat(depth)}</${tag}>`;
          }
          return `<${tag}${attrsStr}>${inner}</${tag}>`;
        }
        if (selfClosedTags === null || selfClosedTags.includes(tag)) {
          return `<${tag}${attrsStr}/>`;
        }
        return `<${tag}${attrsStr}></${tag}>`;
      }
      if (value === null || value === void 0 || value === "") {
        if (selfClosedTags === null || selfClosedTags.includes(tag)) {
          return `<${tag}${attrsStr}/>`;
        }
        return `<${tag}${attrsStr}></${tag}>`;
      }
      const text = this._escapeXml(String(value));
      return `<${tag}${attrsStr}>${text}</${tag}>`;
    }
    /**
     * Sanitize tag name for XML.
     * @private
     */
    _sanitizeTag(tag) {
      if (!tag) return "_none_";
      return tag.replace(/[^a-zA-Z0-9_\-.:]/g, "_");
    }
    /**
     * Escape XML text content.
     * @private
     */
    _escapeXml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
    /**
     * Escape XML attribute value.
     * @private
     */
    _escapeAttr(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    /**
     * Deserialize Bag from XML format.
     *
     * @param {string} source - XML string to parse.
     * @param {Object} [options={}] - Parsing options.
     * @param {string} [options.tagAttribute=null] - If set, save XML tag name as this attribute on each node.
     * @returns {Bag} Reconstructed Bag hierarchy.
     */
    static fromXml(source, options = {}) {
      const { tagAttribute = null } = options;
      let doc;
      if (typeof DOMParser !== "undefined") {
        const parser = new DOMParser();
        doc = parser.parseFromString(source, "application/xml");
        const parseError = doc.querySelector("parsererror");
        if (parseError) {
          throw new Error(`XML parse error: ${parseError.textContent}`);
        }
      } else {
        const parser = new import_xmldom.DOMParser();
        doc = parser.parseFromString(source, "application/xml");
      }
      return this._xmlElementToBag(doc.documentElement, tagAttribute);
    }
    /**
     * Convert XML element to Bag (recursive).
     * @param {Element} element - XML element to convert.
     * @param {string|null} [tagAttribute=null] - If set, save tag name as this attribute.
     * @private
     */
    static _xmlElementToBag(element, tagAttribute = null) {
      const bag = new this();
      const childElements = Array.from(element.childNodes).filter((n) => n.nodeType === 1);
      for (const child of childElements) {
        const originalXmlTag = child.tagName;
        const attr = {};
        for (let i = 0; i < child.attributes.length; i++) {
          const attrNode = child.attributes[i];
          attr[attrNode.name] = attrNode.value;
        }
        const resolver = decodeResolver(attr._resolver);
        if (resolver) delete attr._resolver;
        const isBagValue = String(attr._T || "").toUpperCase() === "BAG";
        Object.assign(attr, decodeAttrs(attr));
        let label = originalXmlTag;
        if ("_tag" in attr) {
          label = attr._tag;
          delete attr._tag;
        }
        if (tagAttribute && tagAttribute in attr) {
          label = attr[tagAttribute];
          delete attr[tagAttribute];
        }
        const requestedLabel = label;
        let suffix = 1;
        while (bag.getNode(label)) {
          label = `${requestedLabel}_${suffix++}`;
        }
        const childChildElements = Array.from(child.childNodes).filter((n) => n.nodeType === 1);
        let node;
        if (childChildElements.length > 0 || isBagValue) {
          const childBag = this._xmlElementToBag(child, tagAttribute);
          node = bag.setItem(label, childBag, Object.keys(attr).length > 0 ? attr : null);
        } else {
          const value = child.textContent || "";
          node = bag.setItem(label, value, Object.keys(attr).length > 0 ? attr : null);
        }
        if (resolver) node.resolver = resolver;
        node.xmlTag = originalXmlTag;
      }
      return bag;
    }
    /**
     * Load Bag from URL. Auto-detects format from content-type.
     *
     * @param {string} url - HTTP/HTTPS URL to fetch.
     * @param {Object} [options={}] - Fetch options.
     * @param {number} [options.timeout=30] - Timeout in seconds.
     * @returns {Promise<Bag>} Parsed content as Bag.
     */
    static async fromUrl(url, options = {}) {
      const { timeout = 30 } = options;
      const fetchOptions = {};
      if (timeout) {
        fetchOptions.signal = AbortSignal.timeout(timeout * 1e3);
      }
      const response = await fetch(url, fetchOptions);
      const contentType = response.headers.get("content-type") || "";
      const text = await response.text();
      if (contentType.includes("json")) {
        return _Bag.fromJson(text);
      }
      if (contentType.includes("xml")) {
        return _Bag.fromXml(text);
      }
      const trimmed = text.trim();
      if (trimmed.startsWith("<")) {
        return _Bag.fromXml(text);
      }
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        return _Bag.fromJson(text);
      }
      throw new BagException(`Unsupported content-type: ${contentType}`);
    }
    // -------------------------------------------------------------------------
    // JSON Serialization
    // -------------------------------------------------------------------------
    /**
     * Serialize Bag to JSON string.
     *
     * Each node becomes {"label": ..., "value": ..., "attr": {...}}.
     * Nested Bags have value as a list of child nodes.
     *
     * @param {boolean} [typed=true] - If true, encode types for date/datetime/Decimal (TYTX).
     * @returns {string} JSON string representation.
     */
    toJson(typed = true) {
      const result = [];
      for (const node of this._nodes) {
        result.push(this._nodeToJsonDict(node, typed));
      }
      if (typed) {
        return toTytx(result);
      }
      return JSON.stringify(result);
    }
    /**
     * Convert a BagNode to JSON-serializable dict (internal).
     * @private
     */
    _nodeToJsonDict(node, typed) {
      let value = node.resolver ? null : node.getValue(true);
      if (value && typeof value._nodeToJsonDict === "function") {
        const childResult = [];
        for (const childNode of value._nodes) {
          childResult.push(value._nodeToJsonDict(childNode, typed));
        }
        value = childResult;
      }
      const result = { label: node.label, value, attr: encodeAttrs(node.attr) };
      if (node.nodeTag !== null) result.tag = node.nodeTag;
      if (node.resolver) result.resolver = encodeResolver(node.resolver);
      return result;
    }
    /**
     * Deserialize JSON to Bag.
     *
     * Accepts JSON string, dict, or list. Recursively converts nested
     * structures to Bag hierarchy.
     *
     * @param {string|Object|Array} source - JSON string, dict or list to parse.
     * @param {string} [listJoiner=null] - If provided, join string arrays with this separator.
     * @returns {Bag} Deserialized Bag.
     */
    static fromJson(source, listJoiner = null) {
      if (typeof source === "string") {
        source = fromTytx(source);
      }
      if (!Array.isArray(source) && typeof source !== "object") {
        source = { value: source };
      }
      return _Bag._fromJsonRecursive(source, listJoiner);
    }
    /**
     * Recursively convert JSON data to Bag (internal).
     * @private
     */
    static _fromJsonRecursive(data, listJoiner = null) {
      if (data instanceof _Bag) return data;
      if (Array.isArray(data)) {
        if (listJoiner !== null && data.every((item) => typeof item === "string")) {
          return data.join(listJoiner);
        }
        if (data.length === 0) {
          return new _Bag();
        }
        if (typeof data[0] === "object" && data[0] !== null && "label" in data[0]) {
          const result2 = new _Bag();
          for (const item of data) {
            const label = item.label;
            const value = _Bag._fromJsonRecursive(item.value, listJoiner);
            const attr = decodeAttrs(item.attr);
            const node = result2.setItem(label, value, attr);
            node.nodeTag = item.tag ?? null;
            const resolver = decodeResolver(item.resolver);
            if (resolver) node.resolver = resolver;
          }
          return result2;
        }
        const result = new _Bag();
        for (let n = 0; n < data.length; n++) {
          result.setItem(`r_${n}`, _Bag._fromJsonRecursive(data[n], listJoiner));
        }
        return result;
      }
      if (typeof data === "object" && data !== null) {
        if (Object.keys(data).length === 0) {
          return new _Bag();
        }
        const result = new _Bag();
        for (const [k, v] of Object.entries(data)) {
          result.setItem(k, _Bag._fromJsonRecursive(v, listJoiner));
        }
        return result;
      }
      return data;
    }
    // -------------------------------------------------------------------------
    // String representation
    // -------------------------------------------------------------------------
    /**
     * Return ASCII tree representation of bag contents.
     *
     * Produces a visual tree structure showing all nodes, their values,
     * and attributes. Handles nested Bags recursively and detects
     * circular references.
     *
     * @param {boolean} [isStatic=true] - If false, triggers resolvers to get current values.
     * @param {Map} [_visited=null] - Internal: tracks visited nodes for circular refs.
     * @param {string} [_prefix=''] - Internal: indentation prefix for nested bags.
     * @param {boolean} [_isLast=true] - Internal: whether this is the last sibling.
     * @returns {string} ASCII tree representation.
     *
     * @example
     * const bag = new Bag();
     * bag.setItem('user.age', 30);
     * bag.setItem('user.city', 'Rome');
     * console.log(bag.toStringTree());
     * // user
     * // ├── age: 30
     * // └── city: 'Rome'
     */
    toStringTree(isStatic = true, _visited = null, _prefix = "", _isLast = true) {
      if (_visited === null) {
        _visited = /* @__PURE__ */ new Map();
      }
      const lines = [];
      const nodes = [...this._nodes];
      for (let idx = 0; idx < nodes.length; idx++) {
        const node = nodes[idx];
        const isLast = idx === nodes.length - 1;
        const value = node.getValue(isStatic);
        const attrs = node.getAttr();
        let attrStr = "";
        const attrKeys = Object.keys(attrs);
        if (attrKeys.length > 0) {
          const attrParts = attrKeys.map((k) => `${k}=${JSON.stringify(attrs[k])}`);
          attrStr = " [" + attrParts.join(", ") + "]";
        }
        const branch = isLast ? "\u2514\u2500\u2500 " : "\u251C\u2500\u2500 ";
        const childPrefix = _prefix + (isLast ? "    " : "\u2502   ");
        if (value instanceof _Bag) {
          const nodeId = node;
          const backref = value.backref ? "(*)" : "";
          if (_visited.has(nodeId)) {
            lines.push(`${_prefix}${branch}${node.label}${backref}${attrStr} \u2192 (circular ref)`);
          } else {
            _visited.set(nodeId, node.label);
            lines.push(`${_prefix}${branch}${node.label}${backref}${attrStr}`);
            const inner = value.toStringTree(isStatic, _visited, childPrefix, isLast);
            if (inner) {
              lines.push(inner);
            }
          }
        } else {
          let valueStr;
          if (value === null) {
            valueStr = "null";
          } else if (value === void 0) {
            valueStr = "undefined";
          } else if (value instanceof ArrayBuffer || value instanceof Uint8Array) {
            const decoder = new TextDecoder("utf-8", { fatal: false });
            const bytes = value instanceof ArrayBuffer ? new Uint8Array(value) : value;
            valueStr = decoder.decode(bytes);
          } else if (typeof value === "string") {
            if (value.length > 50) {
              valueStr = JSON.stringify(value.slice(0, 47) + "...");
            } else {
              valueStr = JSON.stringify(value);
            }
          } else {
            valueStr = String(value);
          }
          lines.push(`${_prefix}${branch}${node.label}: ${valueStr}${attrStr}`);
        }
      }
      return lines.join("\n");
    }
    /**
     * Return ASCII tree representation of bag contents.
     *
     * @param {boolean} [isStatic=true] - If false, trigger resolvers.
     * @param {Object} [_visited=null] - Internal: tracks visited nodes for circular refs.
     * @param {string} [_prefix=''] - Internal: indentation prefix.
     * @returns {string} ASCII tree string.
     */
    toString(isStatic = true, _visited = null, _prefix = "") {
      if (!_visited) {
        _visited = /* @__PURE__ */ new Set();
      }
      const lines = [];
      const nodes = [...this._nodes];
      for (let idx = 0; idx < nodes.length; idx++) {
        const node = nodes[idx];
        const isLast = idx === nodes.length - 1;
        const value = node.getValue(isStatic);
        let attrStr = "";
        const attrs = node.attr;
        if (attrs && Object.keys(attrs).length > 0) {
          const parts = Object.entries(attrs).map(([k, v]) => `${k}=${JSON.stringify(v)}`);
          attrStr = ` [${parts.join(", ")}]`;
        }
        const branch = isLast ? "\u2514\u2500\u2500 " : "\u251C\u2500\u2500 ";
        const childPrefix = _prefix + (isLast ? "    " : "\u2502   ");
        if (value && typeof value._htraverse === "function") {
          const nodeId = node;
          if (_visited.has(nodeId)) {
            lines.push(`${_prefix}${branch}${node.label}${attrStr} \u2192 (circular ref)`);
          } else {
            _visited.add(nodeId);
            lines.push(`${_prefix}${branch}${node.label}${attrStr}`);
            const inner = value.toString(isStatic, _visited, childPrefix);
            if (inner) {
              lines.push(inner);
            }
          }
        } else {
          let valueStr;
          if (value === null || value === void 0) {
            valueStr = "null";
          } else if (typeof value === "string" && value.length > 50) {
            valueStr = JSON.stringify(value.slice(0, 47) + "...");
          } else if (typeof value === "string") {
            valueStr = JSON.stringify(value);
          } else {
            valueStr = String(value);
          }
          lines.push(`${_prefix}${branch}${node.label}: ${valueStr}${attrStr}`);
        }
      }
      return lines.join("\n");
    }
  };
  __publicField(_Bag, "tytxSuffix", "X");
  var Bag = _Bag;
  var BagException = class extends Error {
    constructor(message) {
      super(message);
      this.name = "BagException";
    }
  };
  BagResolver.registerBagClass(Bag);
  registerClass(Bag);

  // src/resolvers/UrlResolver.js
  var UrlResolver = class extends BagResolver {
    /**
     * Create a URL resolver.
     *
     * @param {string|Object} urlOrKwargs - URL string or options object.
     * @param {Object} [kwargs] - Additional options if first arg is URL.
     */
    constructor(urlOrKwargs, kwargs = {}) {
      if (typeof urlOrKwargs === "string") {
        kwargs = { ...kwargs, url: urlOrKwargs };
      } else {
        kwargs = urlOrKwargs || {};
      }
      super(kwargs);
    }
    /**
     * Load data from URL.
     *
     * @param {Object} kwargs - Parameters for this load call.
     * @returns {Promise<*>} Response data.
     */
    async load(kwargs) {
      let url = this._kw.url;
      const method = this._kw.method;
      const qs = this._kw.qs;
      const timeout = this._kw.timeout;
      const transport = this._kw.transport;
      let body = this._kw.body;
      if (kwargs._body !== void 0) {
        body = kwargs._body;
      }
      const pathArgs = [];
      const extraQs = {};
      for (const [key, value] of Object.entries(kwargs)) {
        if (key.startsWith("arg_") && value !== null && value !== void 0) {
          const idx = parseInt(key.slice(4), 10);
          if (!isNaN(idx)) {
            while (pathArgs.length <= idx) {
              pathArgs.push(null);
            }
            pathArgs[idx] = value;
          }
        } else if (!this.constructor.classKwargs.hasOwnProperty(key) && !this.constructor.internalParams.has(key) && !key.startsWith("_")) {
          if (value !== null && value !== void 0) {
            extraQs[key] = value;
          }
        }
      }
      if (pathArgs.length > 0 && url.includes("{")) {
        const placeholders = url.match(/\{([^}]+)\}/g) || [];
        placeholders.forEach((placeholder, i) => {
          if (i < pathArgs.length && pathArgs[i] !== null) {
            url = url.replace(placeholder, String(pathArgs[i]));
          }
        });
      }
      const mergedQs = {};
      if (qs) {
        Object.assign(mergedQs, this._qsToDict(qs));
      }
      Object.assign(mergedQs, extraQs);
      if (Object.keys(mergedQs).length > 0) {
        const params = new URLSearchParams();
        for (const [key, value] of Object.entries(mergedQs)) {
          if (value !== null && value !== void 0) {
            params.append(key, String(value));
          }
        }
        const separator = url.includes("?") ? "&" : "?";
        url = `${url}${separator}${params.toString()}`;
      }
      const fetchOptions = {
        method: method.toUpperCase(),
        transport
      };
      if (timeout) {
        fetchOptions.signal = AbortSignal.timeout(timeout * 1e3);
      }
      if (body !== null && body !== void 0) {
        fetchOptions.body = body;
      }
      const response = await fetchTytx(url, fetchOptions);
      return response;
    }
    /**
     * Convert query string source to dict, filtering null/undefined values.
     *
     * @param {Object|Map} qs - Query string parameters.
     * @returns {Object} Parameters with null/undefined values removed.
     * @private
     */
    _qsToDict(qs) {
      if (!qs) return {};
      if (typeof qs.keys === "function" && typeof qs.getItem === "function") {
        const result2 = {};
        for (const k of qs.keys()) {
          const v = qs.getItem(k);
          if (v !== null && v !== void 0) {
            result2[k] = v;
          }
        }
        return result2;
      }
      const result = {};
      for (const [k, v] of Object.entries(qs)) {
        if (v !== null && v !== void 0) {
          result[k] = v;
        }
      }
      return result;
    }
  };
  __publicField(UrlResolver, "classKwargs", {
    cacheTime: 300,
    readOnly: true,
    retryPolicy: {
      maxAttempts: 3,
      delay: 1,
      backoff: 2,
      jitter: true,
      on: ["TypeError", "NetworkError", "AbortError"]
    },
    asBag: false,
    url: null,
    method: "get",
    qs: null,
    body: null,
    timeout: 5,
    // seconds (same unit as Python)
    transport: "json"
  });
  __publicField(UrlResolver, "classArgs", ["url"]);
  __publicField(UrlResolver, "internalParams", /* @__PURE__ */ new Set([
    "cacheTime",
    "readOnly",
    "retryPolicy",
    "asBag",
    "url",
    "method",
    "qs",
    "body",
    "timeout",
    "transport"
  ]));

  // src/browser-uuid.js
  function randomUUID() {
    return globalThis.crypto.randomUUID();
  }

  // src/resolvers/UuidResolver.js
  var UuidResolver = class extends BagResolver {
    load() {
      return randomUUID();
    }
  };
  __publicField(UuidResolver, "classKwargs", {
    cacheTime: -1,
    readOnly: false,
    asBag: false,
    retryPolicy: null,
    version: "uuid4"
  });
  __publicField(UuidResolver, "classArgs", ["version"]);
  __publicField(UuidResolver, "internalParams", /* @__PURE__ */ new Set([
    "cacheTime",
    "readOnly",
    "asBag",
    "retryPolicy",
    "version"
  ]));

  // src/resolvers/StorageResolver.js
  var StorageResolver = class extends BagResolver {
    /**
     * Create a StorageResolver.
     *
     * @param {string|Object} keyOrKwargs - Storage key or options object.
     * @param {Object} [kwargs] - Additional options if first arg is key.
     */
    constructor(keyOrKwargs, kwargs = {}) {
      if (typeof keyOrKwargs === "string") {
        kwargs = { ...kwargs, key: keyOrKwargs };
      } else {
        kwargs = keyOrKwargs || {};
      }
      super(kwargs);
    }
    /**
     * Get the storage backend.
     *
     * @returns {Storage|null} localStorage or sessionStorage, or null if unavailable.
     * @private
     */
    _getStorage(kwargs) {
      const type = kwargs.storageType || "local";
      if (type === "session") {
        return typeof sessionStorage !== "undefined" ? sessionStorage : null;
      }
      return typeof localStorage !== "undefined" ? localStorage : null;
    }
    /**
     * Load value from Web Storage.
     *
     * @param {Object} kwargs - Parameters (key can be overridden via node attrs).
     * @returns {*} The stored value, or defaultValue if not found.
     */
    load(kwargs) {
      const key = kwargs.key;
      const defaultValue = kwargs.defaultValue;
      const storage = key ? this._getStorage(kwargs) : null;
      const stored = storage ? storage.getItem(key) : null;
      const value = stored !== null ? stored : defaultValue;
      if (kwargs.dtype == null || value == null) return value;
      const text = String(value);
      if (kwargs.dtype === "L" && !/^[+-]?\d+(?:_\d+)*$/.test(text.trim())) {
        throw new TypeError(`Invalid integer in Web Storage: ${text}`);
      }
      if (kwargs.dtype === "R" && !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text.trim())) {
        throw new TypeError(`Invalid real number in Web Storage: ${text}`);
      }
      const input = kwargs.dtype === "L" ? text.replaceAll("_", "") : text;
      const converted = fromTytx(`${input}::${kwargs.dtype}`);
      if (typeof converted === "number" && Number.isNaN(converted) || converted instanceof Date && Number.isNaN(converted.getTime())) {
        throw new TypeError(`Invalid ${kwargs.dtype} value in Web Storage: ${text}`);
      }
      return converted;
    }
  };
  __publicField(StorageResolver, "classKwargs", {
    cacheTime: -1,
    readOnly: true,
    asBag: false,
    retryPolicy: null,
    key: null,
    storageType: "local",
    defaultValue: null,
    dtype: null
  });
  __publicField(StorageResolver, "classArgs", ["key"]);
  __publicField(StorageResolver, "internalParams", /* @__PURE__ */ new Set([
    "cacheTime",
    "readOnly",
    "asBag",
    "retryPolicy"
  ]));

  // src/browser.js
  setDecimalLibrary("number");
  var version = "0.7.0";
  return __toCommonJS(browser_exports);
})();
//# sourceMappingURL=genro-bag.browser.js.map
