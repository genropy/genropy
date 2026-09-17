"""Optional TYTX transport for RPC Bag envelopes and parameters."""


PARAMETER_SUFFIX = '::BAGTYTX'
CONTENT_TYPE = 'application/vnd.genro.bag+tytx'


def transport_format(application, page=None):
    value = application.experimentalValue('bag_transport', 'format') or 'xml'
    if value not in ('xml', 'tytx'):
        raise ValueError(f'Unsupported Bag transport: {value}')
    if page is not None:
        from gnr.web.gnrjsassets import bag_javascript_implementation
        if bag_javascript_implementation(page) != 'genro-bag-js-mixin':
            return 'xml'
    if value == 'tytx':
        if (application.experimentalValue('bag', 'implementation') != 'genro-bag'
                or application.experimentalValue('bag_js', 'implementation') != 'genro-bag-js-mixin'):
            raise ValueError('TYTX transport requires genro-bag and genro-bag-js-mixin')
    if value == 'tytx' and application.config.getItem('experimental-features?dojo-xhr-patch') != 'fetch':
        raise ValueError('TYTX transport requires the fetch HTTP transport')
    return value


def encode_envelope(envelope, localize):
    """Encode the adapter rows as UTF-8 textual TYTX using the JSON codec."""
    from genro_tytx import to_tytx

    payload = envelope.to_genropy_js(translator=localize)
    return to_tytx(payload, transport=None).encode('utf-8')


def decode_parameter(value, application):
    """Decode only explicitly configured TYTX parameters; resolvers remain inert."""
    if transport_format(application) != 'tytx':
        raise ValueError('TYTX Bag parameters are disabled')
    from gnr.core.gnrbag import Bag
    return Bag.from_tytx(value[:-len(PARAMETER_SUFFIX)], transport='json')
