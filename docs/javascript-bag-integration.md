# Opt-in JavaScript Bag integration

The legacy JavaScript Bag remains the default. The only standalone integration
uses the browser bundle and the lightweight framework mixin:

```xml
<experimental>
    <bag_js implementation="genro-bag-js-mixin"/>
</experimental>
```

Supported values are `legacy` and `genro-bag-js-mixin`. Missing configuration
selects `legacy`; other values fail explicitly. The obsolete `genro-bag-js`
adapter selection has been removed rather than silently redirected.
The selected files load before DOM source, stores, RPC and widgets in both
development and compressed modes. No instance configuration is changed by this PR.

## Browser bundle

The checked-in bundle contains genro-bag-js 0.7.0 and one genro-tytx registry.
Decimal decoding uses JavaScript Number for existing widgets. Rebuild from
the matching library checkout using locked dependencies:

```sh
npm ci
npm run build:browser
cp dist/genro-bag.browser.js /path/to/genropy/gnrjs/gnr_d11/js/genro_bagjs_bundle.js
cp dist/genro-bag.browser.js.map /path/to/genropy/gnrjs/gnr_d11/js/genro-bag.browser.js.map
```

No CDN or sibling checkout is required at runtime. The standalone container
keeps its dictionary and ordered list, as in Python. Framework callers use
`getNodes()` instead of private array access.

See [the mixin boundary](javascript-bag-mixin.md) and
[JSON/TYTX transport](bag-tytx-transport.md) for configuration and scope.
Historical compatibility inventories describe earlier observations, not a
second supported implementation or a guarantee of full application parity.

## Page-local selection

See [page-local Bag JavaScript selection](page-bag-javascript-selection.md) for
instance defaults, page overrides and the standalone `bag_native` frontend.
