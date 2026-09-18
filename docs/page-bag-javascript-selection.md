# Page-local Bag JavaScript selection (D21)

One HTML page loads one Bag variant. A server may serve pages using different
variants. The standalone package remains unchanged: Genro compatibility is
composed only when selecting GenroJS page assets.

## Existing GenroJS pages

The instance default remains:

```xml
<experimental>
    <bag_js implementation="genro-bag-js-mixin"/>
</experimental>
```

Missing configuration selects `legacy`. A page can override that default in
its Python class, without changing the application or other pages:

```python
class GnrCustomWebPage:
    bag_js_implementation = 'legacy'  # or 'genro-bag-js-mixin'
```

This is a server-side page attribute, not a URL argument. The mixin variant
loads `genro_bagjs_bundle.js`, then `gnrbag_mixin.js`, then GenroJS consumers.
Legacy loads `gnrbag.js` and the usual GenroJS consumers.

## Standalone Bag pages

A custom page using its own UI instead of GenroClient selects:

```python
class GnrCustomWebPage:
    page_frontend = 'bag_native'
    pagetemplate = 'my_native_page.tpl'
```

Place that template in the application's normal template search path. It must
render the generated `genroJsImport` URLs and initialize its own UI. For example,
the relevant Mako fragment is:

```html
% for url in genroJsImport:
<script src="${url | h}"></script>
% endfor
<script>
    const bag = new GenroBagJS.Bag();
    bag.setItem('message', 'Standalone Bag');
</script>
```

This frontend loads only the standalone browser bundle, without `gnrbag.js`,
`gnrbag_mixin.js`, Dojo importer or GenroClient consumers. It ignores the
instance's mixin default. The standard template is rejected because it starts
GenroClient and requires the adapted classes. A custom template must not add
legacy/mixin scripts itself. No coexistence of variants within a page is promised.

## Transport and compressed assets

The Genro-specific TYTX RPC envelope is selected only for mixin pages when the
instance enables it. Legacy and native custom pages retain XML RPC envelopes;
native pages must implement their own client handling rather than loading
Genro RPC consumers. This change does not introduce a new native RPC protocol.
Parameter decoding retains its existing instance-level configuration gate.

Compressed bundles are cached by the ordered full source-path list, not a
single site-wide URL. Native, mixin, legacy and different source versions cannot
reuse each other's bundle entry. Debug mode recompresses; normal source-update
invalidation still follows the existing server restart workflow.

Tests cover same-application selection, native asset exclusions, cache isolation,
standard-template rejection and page-local RPC format selection.
