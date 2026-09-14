# Experimental TYTX RPC transport

Enable on an instance using both new Bag implementations:

```xml
<experimental-features dojo-xhr-patch="fetch"/>
<experimental>
    <bag implementation="genro-bag"/>
    <bag_js implementation="genro-bag-js-mixin"/>
    <bag_transport format="tytx"/>
</experimental>
```

Omitting `bag_transport`, or selecting `format="xml"`, keeps XML. Invalid
combinations fail explicitly. Restart the instance and reload its pages when
changing this option; do not mix pages loaded under different configurations.

This option covers normal HTTP RPC Bag envelopes (including main DOM source,
results, errors and client data changes) and top-level Bag parameters. It does
not replace explicit XML exports, WebSocket messages, ping responses, uploads,
or Bag values embedded inside ordinary JSON objects.

RPC responses contain textual TYTX (JSON with typed values), with content type
`application/vnd.genro.bag+tytx`. The fetch switch reads the response as text;
synchronous calls use the existing XHR path. Top-level Bag parameters contain
TYTX JSON followed by `::BAGTYTX` in ordinary form fields. No base64 or
MessagePack response fallback is used. XML ping responses remain supported.

Server serialization uses the Bag node flattener followed by a GenroPy
reference iterator and a translation iterator, then the TYTX encoder. It does
not build an intermediate Bag. Envelope attributes remain part of the rows.
Callable RPC references remain opaque strings on the client. Decimal values
are temporarily converted to JavaScript numbers for legacy widgets.

Strings containing valid TYTX type suffixes are interpreted according to the
TYTX contract; preserving those suffixes as literal text is an accepted limit.

Legacy Python resolver subclasses overriding `resolverSerialize()` remain
supported by the GenroPy bridge, with a `DeprecationWarning` requesting a move
to `serialize()`. The bridge normalizes descriptor keys and permits legacy
overrides to call `super()` without recursion. Native `serialize()` overrides
retain precedence.

The framework codec carries remote resolver descriptions as metadata and
reconstructs them through the existing RPC resolver factory. It does not load
Python resolver implementations received from the browser. DOM source classes,
localization and cached relation metadata are preserved by the framework bridge.

Cross-language tests use Python's encoder, the actual browser bundle, and
Python's decoder. A live application acceptance run is still required before
using this experimentally beyond a test instance.
