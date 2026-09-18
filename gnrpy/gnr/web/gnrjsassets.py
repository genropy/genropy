"""Page-local JavaScript selection and asset-set-aware bundle caching."""


def bag_javascript_implementation(page):
    if getattr(page, 'page_frontend', None) == 'bag_native':
        return 'genro-bag-js-native'
    implementation = getattr(page, 'bag_js_implementation', None)
    if implementation is None:
        implementation = page.application.experimentalValue('bag_js', 'implementation')
    implementation = implementation or 'legacy'
    if implementation not in ('legacy', 'genro-bag-js-mixin'):
        raise ValueError(f'Unsupported JavaScript Bag implementation: {implementation}')
    return implementation


def bag_javascript_files(page):
    implementation = bag_javascript_implementation(page)
    if implementation == 'legacy':
        return ['gnrbag']
    if implementation == 'genro-bag-js-native':
        return ['genro_bagjs_bundle']
    return ['genro_bagjs_bundle', 'gnrbag_mixin']


def compressed_javascript_url(page, jsfiles):
    """Preserve the legacy site cache; isolate opt-in bundles by asset list."""
    if bag_javascript_implementation(page) == 'legacy':
        if not page.site.compressedJsPath or page.site.debug:
            page.site.compressedJsPath = page.jstools.compress(jsfiles)
        return page.site.compressedJsPath
    cache = getattr(page.site, '_compressed_js_by_files', None)
    if cache is None:
        cache = page.site._compressed_js_by_files = {}
    key = tuple(jsfiles)
    if key not in cache or page.site.debug:
        cache[key] = page.jstools.compress(jsfiles)
    return cache[key]
