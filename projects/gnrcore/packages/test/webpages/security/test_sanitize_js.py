# -*- coding: utf-8 -*-

"""Test page for stripJsFromHtml sanitization and grid rendering with sanitize_js switch"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'Test sanitize_js'

    def prepareForm(self, root):
        root.data('gnr.switches', None, sanitize_js=True)

    def test_1_stripJsFromHtml_regex(self, pane):
        """stripJsFromHtml: regex unit tests"""
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top', height='40px', padding='5px')
        top.button('Run tests', action='FIRE .run_tests;')
        top.div('^.test_result', margin_left='10px', display='inline-block',
                font_size='14px', font_weight='bold')

        center = bc.contentPane(region='center', padding='10px', overflow='auto')
        center.div(nodeId='test_results',
                   style='font-family:monospace; font-size:13px; white-space:pre-wrap;')

        pane.dataController("""
            var passed = 0;
            var failed = 0;
            var log = [];

            function check(label, input, expected) {
                var result = stripJsFromHtml(input);
                if (result === expected) {
                    passed++;
                    log.push('PASS: ' + label);
                } else {
                    failed++;
                    log.push('FAIL: ' + label);
                    log.push('  input:    ' + JSON.stringify(input));
                    log.push('  expected: ' + JSON.stringify(expected));
                    log.push('  got:      ' + JSON.stringify(result));
                }
            }

            // --- Script tags ---
            check('strip simple script tag',
                '<b>hello</b><script>alert(1)</script>',
                '<b>hello</b>');
            check('strip script tag with attributes',
                '<div><script type="text/javascript">document.cookie</script></div>',
                '<div></div>');
            check('strip multiline script',
                'text<script>\\nvar x=1;\\nalert(x);\\n</script>end',
                'textend');

            // --- Event handlers ---
            check('strip onerror attribute',
                '<img src="x" onerror="alert(1)">',
                '<img src="x" >');
            check('strip onclick attribute',
                '<div onclick="evil()">text</div>',
                '<div >text</div>');
            check('strip onmouseover with single quotes',
                "<a onmouseover='steal()'>link</a>",
                '<a >link</a>');
            check('strip onload without quotes',
                '<body onload=init()>',
                '<body >');

            // --- javascript: URIs ---
            check('strip javascript href',
                '<a href="javascript:alert(1)">click</a>',
                '<a href="#">click</a>');
            check('strip javascript src',
                '<iframe src="javascript:alert(1)">',
                '<iframe src="">');
            check('strip javascript href with spaces',
                '<a href=" javascript:void(0)">x</a>',
                '<a href="#">x</a>');

            // --- Safe HTML preserved ---
            check('preserve bold tag',
                '<b>bold text</b>',
                '<b>bold text</b>');
            check('preserve anchor with https',
                '<a href="https://example.com">link</a>',
                '<a href="https://example.com">link</a>');
            check('preserve br and img with real src',
                '<br><img src="https://img.com/photo.jpg">',
                '<br><img src="https://img.com/photo.jpg">');
            check('preserve plain text',
                'just plain text',
                'just plain text');
            check('preserve empty string',
                '',
                '');

            // --- Non-string passthrough ---
            check('passthrough number',
                42, 42);
            check('passthrough null',
                null, null);
            check('passthrough undefined',
                undefined, undefined);

            // --- Combined attack vectors ---
            check('combined: script + event + javascript uri',
                '<div><script>alert(1)</script><img onerror="x"><a href="javascript:y">z</a></div>',
                '<div><img ><a href="#">z</a></div>');

            var summary = 'Passed: ' + passed + '/' + (passed + failed);
            if (failed > 0) {
                summary = 'FAILED ' + failed + ' test(s). ' + summary;
            } else {
                summary = 'ALL TESTS PASSED. ' + summary;
            }
            SET .test_result = summary;
            genro.nodeById('test_results').domNode.innerHTML = log.join('\\n');
        """, _fired='^.run_tests')

    def test_2_grid_sanitize(self, pane):
        """Grid: sanitize_js in cell rendering"""
        frame = pane.framePane('sanitize_grid', height='500px',
                               datapath='.grid_test')
        frame.data('.store', self._malicious_data())
        frame.includedView(storepath='.store', datapath=False,
                           struct=self._grid_struct, datamode='bag',
                           autoWidth=True)

    def _malicious_data(self):
        result = Bag()
        result['r_0'] = Bag(dict(
            description='Normal text',
            html_content='<b>Bold</b> and <i>italic</i>',
            payload='No attack here',
            active=True,
            btn_label=None,
            tpl_field='<script>alert(1)</script>Safe',
            js_field='some value',
            checked=True,
            chkcell=True
        ))
        result['r_1'] = Bag(dict(
            description='<script>alert("XSS")</script>Injected',
            html_content='<img src=x onerror="alert(1)">evil image',
            payload='<a href="javascript:alert(1)">click me</a>',
            active=False,
            btn_label=None,
            tpl_field='<img onerror="x">Hello',
            js_field='other value',
            checked=False,
            chkcell=False
        ))
        result['r_2'] = Bag(dict(
            description='<div onclick="steal()">click trap</div>',
            html_content='<iframe src="javascript:alert(1)">',
            payload='<script>document.cookie</script><b>safe part</b>',
            active=True,
            btn_label=None,
            tpl_field='<a href="javascript:x">link</a>',
            js_field='third value',
            checked=True,
            chkcell=False
        ))
        result['r_3'] = Bag(dict(
            description='<a href="https://safe.com">safe link</a>',
            html_content='<br><b>clean html</b>',
            payload='plain text value',
            active=False,
            btn_label=None,
            tpl_field='Clean text',
            js_field='fourth value',
            checked=False,
            chkcell=True
        ))
        return result

    def _grid_struct(self, struct):
        r = struct.view().rows()
        r.cell('description', name='Description', width='15em')
        r.cell('html_content', name='HTML Content', width='15em')
        r.cell('payload', name='Payload', width='15em')
        r.cell('active', name='Active', width='5em', dtype='B')
        r.cell('btn_label', name='Button', width='8em',
               format_isbutton='Click me',
               format_buttonclass='buttonInGrid',
               format_onclick="alert('clicked row ' + $1.rowIndex);")
        r.cell('tpl_field', name='Template', width='15em',
               format_template='<b>#</b>')
        r.cell('js_field', name='JS fmt', width='10em',
               js="function(v, row){return '<i>'+v+'</i>';}")
        r.checkboxcolumn('checked', name='ChkCol')
        r.checkboxcell('chkcell', name='ChkCell')

    def test_3_datatemplate_sanitize(self, pane):
        """dataTemplate: sanitize_js in template rendering"""
        center = pane.contentPane(padding='10px', datapath='.tpl_test',
                                  height='400px', overflow='auto')
        center.data('.safe_name', '<b>Giovanni</b> Rossi')
        center.data('.xss_name', '<script>alert(1)</script>Mario')
        center.data('.event_name', '<span onmouseover="steal()">Luigi</span>')
        center.data('.link_name', '<a href="javascript:alert(1)">click</a>')
        center.data('.clean_link', '<a href="https://safe.com">Safe</a>')

        fb = center.formlet(cols=1)

        fb.div('^.safe_tpl_result', lbl='Safe HTML')
        fb.div('^.xss_tpl_result', lbl='Script injection')
        fb.div('^.event_tpl_result', lbl='Event handler')
        fb.div('^.link_tpl_result', lbl='Javascript URI')
        fb.div('^.clean_tpl_result', lbl='Clean link')

        center.dataFormula('.safe_tpl_result',
                           'dataTemplate("Name: $safe_name", data)',
                           data='=.', _onStart=True)
        center.dataFormula('.xss_tpl_result',
                           'dataTemplate("Name: $xss_name", data)',
                           data='=.', _onStart=True)
        center.dataFormula('.event_tpl_result',
                           'dataTemplate("Name: $event_name", data)',
                           data='=.', _onStart=True)
        center.dataFormula('.link_tpl_result',
                           'dataTemplate("Name: $link_name", data)',
                           data='=.', _onStart=True)
        center.dataFormula('.clean_tpl_result',
                           'dataTemplate("Name: $clean_link", data)',
                           data='=.', _onStart=True)
