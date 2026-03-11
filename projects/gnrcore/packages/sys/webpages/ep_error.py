# -*- coding: utf-8 -*-
from xml.sax.saxutils import escape
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    auth_tags = '_DEV_,admin'
    skip_connection = False

    def rootPage(self, error_code=None, error_id=None, *args, **kwargs):
        self.response.content_type = 'text/html; charset=utf-8'
        if not error_code and not error_id:
            return self._render_page('Missing parameter', '<p>No error_code or error_id provided.</p>')
        tblobj = self.db.table('sys.error')
        if error_code:
            rec = tblobj.record(where='$error_code = :ec', ec=error_code,
                                ignoreMissing=True).output('bag')
        else:
            rec = tblobj.record(error_id, ignoreMissing=True).output('bag')
        if not rec:
            lookup_value = error_code or error_id
            return self._render_page('Not Found',
                '<p>No error found with code: <strong>%s</strong></p>' % escape(str(lookup_value)))
        return self._render_record(rec)

    def _render_record(self, rec):
        error_code = rec['error_code'] or ''
        description = rec['description'] or ''
        error_type = rec['error_type'] or ''
        username = rec['username'] or ''
        user_ip = rec['user_ip'] or ''
        user_agent = rec['user_agent'] or ''
        request_uri = rec['request_uri'] or ''
        rpc_method = rec['rpc_method'] or ''
        page_id = rec['page_id'] or ''
        ins_ts = rec['__ins_ts'] or ''
        error_data = rec['error_data']
        traceback_html = self._render_traceback(error_data)
        traceback_xml = error_data.toXml() if isinstance(error_data, Bag) else str(error_data or '')
        sourcerer_url = self.site.config['sourcerer?url'] or ''
        sourcerer_token = self.site.config['sourcerer?token'] or ''
        ask_btn = ''
        if sourcerer_url:
            import json as json_mod
            ask_btn = '''<button id="ask-sourcerer-btn" class="ask-sourcerer-btn" onclick="askSourcerer()">
                Ask Sourcerer</button>'''
            traceback_xml_json = json_mod.dumps(traceback_xml)
        else:
            traceback_xml_json = '""'
        body = '''
        <div class="error-header">
            <div class="error-header-row">
                <div>
                    <h1>Error: {error_code}</h1>
                    <p class="description">{description}</p>
                </div>
                {ask_btn}
            </div>
        </div>
        <div class="info-grid">
            <div class="info-item"><span class="label">Type</span><span class="value">{error_type}</span></div>
            <div class="info-item"><span class="label">Date</span><span class="value">{ins_ts}</span></div>
            <div class="info-item"><span class="label">User</span><span class="value">{username}</span></div>
            <div class="info-item"><span class="label">IP</span><span class="value">{user_ip}</span></div>
            <div class="info-item"><span class="label">RPC Method</span><span class="value">{rpc_method}</span></div>
            <div class="info-item"><span class="label">Page ID</span><span class="value">{page_id}</span></div>
        </div>
        <div class="info-row">
            <span class="label">Request URI</span><span class="value">{request_uri}</span>
        </div>
        <div class="info-row">
            <span class="label">User Agent</span><span class="value">{user_agent}</span>
        </div>
        <div class="traceback-section">
            <div class="traceback-header">
                <h2>Traceback</h2>
                <div class="traceback-actions">
                    <button onclick="expandAll()" class="tb-btn">Expand All</button>
                    <button onclick="collapseAll()" class="tb-btn">Collapse All</button>
                </div>
            </div>
            {traceback_html}
        </div>
        <div id="sourcerer-result" class="sourcerer-result" style="display:none;"></div>
        '''.format(
            error_code=escape(str(error_code)),
            description=escape(str(description)),
            error_type=escape(str(error_type)),
            ins_ts=escape(str(ins_ts)),
            username=escape(str(username)),
            user_ip=escape(str(user_ip)),
            request_uri=escape(str(request_uri)),
            rpc_method=escape(str(rpc_method)),
            page_id=escape(str(page_id)),
            user_agent=escape(str(user_agent)),
            traceback_html=traceback_html,
            ask_btn=ask_btn
        )
        return self._render_page('Error: %s' % escape(str(error_code)), body,
                                  sourcerer_url=sourcerer_url,
                                  sourcerer_token=sourcerer_token,
                                  traceback_xml_json=traceback_xml_json)

    def _render_traceback(self, error_data):
        if not error_data:
            return '<p class="no-traceback">No traceback available.</p>'
        if not isinstance(error_data, Bag):
            try:
                error_data = Bag(error_data)
            except Exception:
                return '<pre class="traceback-plain">%s</pre>' % escape(str(error_data))
        return self._render_bag_traceback(error_data)

    def _render_bag_traceback(self, bag):
        if bag['root'] and isinstance(bag['root'], Bag):
            bag = bag['root']
        parts = []
        nodes = list(bag)
        frame_nodes = [n for n in nodes if isinstance(n.value, Bag) and n.value['lineno']]
        total_frames = len(frame_nodes)

        for node in nodes:
            value = node.value
            label = node.label
            if isinstance(value, Bag) and value['lineno']:
                frame_idx = frame_nodes.index(node)
                is_last = (frame_idx == total_frames - 1)
                parts.append(self._render_frame(value, frame_idx, is_last))
            else:
                text = str(value or label)
                parts.append(
                    '<div class="tb-error-message">%s</div>' % escape(text)
                )
        return '\n'.join(parts)

    def _render_frame(self, frame_bag, index, is_last):
        module = frame_bag['module'] or ''
        filename = frame_bag['filename'] or ''
        file_hash = frame_bag['file_hash'] or ''
        lineno = frame_bag['lineno'] or ''
        name = frame_bag['name'] or ''
        line = frame_bag['line'] or ''
        locals_bag = frame_bag['locals']
        open_attr = ' open' if is_last else ''
        has_locals = locals_bag and len(locals_bag) > 0
        locals_html = self._render_locals(locals_bag) if has_locals else ''
        locals_badge = (' <span class="tb-locals-badge" title="Has local variables">'
                       '%d vars</span>' % len(locals_bag)) if has_locals else ''
        hash_html = (' <span class="tb-hash" title="SHA256 file hash">%s</span>'
                     % escape(str(file_hash))) if file_hash else ''
        name_html = (' <span class="tb-func">%s</span>'
                     % escape(str(name))) if name else ''
        code_html = ('<pre class="tb-code">%s</pre>' % escape(str(line))) if line else ''
        filename_html = ('<div class="tb-filename" title="%s">%s</div>'
                        % (escape(str(filename)), escape(str(filename)))) if filename else ''

        return '''<details class="tb-frame"{open_attr}>
    <summary class="tb-frame-summary">
        <span class="tb-frame-num">#{index}</span>
        <span class="tb-module">{module}</span>
        <span class="tb-separator">:</span>
        <span class="tb-lineno">{lineno}</span>
        {name_html}{hash_html}{locals_badge}
    </summary>
    <div class="tb-frame-body">
        {filename_html}
        {code_html}
        {locals_html}
    </div>
</details>'''.format(
            open_attr=open_attr,
            index=index,
            module=escape(str(module)),
            lineno=escape(str(lineno)),
            name_html=name_html,
            hash_html=hash_html,
            locals_badge=locals_badge,
            filename_html=filename_html,
            code_html=code_html,
            locals_html=locals_html
        )

    def _render_locals(self, locals_bag):
        if not locals_bag:
            return ''
        rows = []
        for node in locals_bag:
            k = node.label
            v = node.value
            v_str = str(v) if v is not None else 'None'
            is_special = v_str.startswith('*') and v_str.endswith('*')
            if len(v_str) > 200:
                v_str = v_str[:200] + '...'
            css_class = ' class="special-value"' if is_special else ''
            rows.append(
                '<tr><td class="loc-name">%s</td>'
                '<td class="loc-value"%s>%s</td></tr>'
                % (escape(str(k)), css_class, escape(v_str))
            )
        return '''<div class="tb-locals">
    <div class="tb-locals-header" onclick="this.parentElement.classList.toggle('expanded')">
        <span class="tb-locals-toggle">&#9654;</span> Local variables ({count})
    </div>
    <table class="tb-locals-table">
        <thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</div>'''.format(count=len(locals_bag), rows='\n'.join(rows))

    def _render_page(self, title, body, sourcerer_url='', sourcerer_token='',
                      traceback_xml_json='""'):
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f0f2f5; color: #333; padding: 24px;
            max-width: 1200px; margin: 0 auto;
        }}

        /* --- Header --- */
        .error-header {{
            background: white; border-radius: 12px; padding: 24px;
            margin-bottom: 16px; border-left: 5px solid #ef4444;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .error-header h1 {{ font-size: 22px; color: #ef4444; margin-bottom: 8px; }}
        .error-header .description {{ font-size: 15px; color: #555; line-height: 1.5; }}

        /* --- Info grid --- */
        .info-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 12px; margin-bottom: 16px;
        }}
        .info-item {{
            background: white; border-radius: 8px; padding: 14px 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        }}
        .info-item .label {{
            display: block; font-size: 10px; text-transform: uppercase;
            letter-spacing: 0.5px; color: #999; margin-bottom: 4px; font-weight: 700;
        }}
        .info-item .value {{ font-size: 14px; color: #333; word-break: break-all; }}
        .info-row {{
            background: white; border-radius: 8px; padding: 10px 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 16px;
            display: flex; align-items: center; gap: 12px;
        }}
        .info-row .label {{
            font-size: 10px; text-transform: uppercase;
            letter-spacing: 0.5px; color: #999; font-weight: 700; flex-shrink: 0;
        }}
        .info-row .value {{ font-size: 13px; color: #555; }}

        /* --- Traceback section --- */
        .traceback-section {{
            background: white; border-radius: 12px; padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .traceback-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px;
        }}
        .traceback-header h2 {{ font-size: 17px; color: #333; }}
        .traceback-actions {{ display: flex; gap: 8px; }}
        .tb-btn {{
            padding: 5px 12px; border: 1px solid #ddd; border-radius: 6px;
            background: #f8f9fa; font-size: 12px; cursor: pointer;
            color: #555; transition: all 0.15s;
        }}
        .tb-btn:hover {{ background: #e9ecef; border-color: #ccc; }}

        /* --- Frame (details/summary) --- */
        .tb-frame {{
            margin-bottom: 8px; border: 1px solid #e5e7eb;
            border-radius: 8px; overflow: hidden;
            transition: border-color 0.15s;
        }}
        .tb-frame[open] {{ border-color: #cbd5e1; }}
        .tb-frame:last-of-type {{ border-color: #f87171; }}

        .tb-frame-summary {{
            padding: 10px 16px; cursor: pointer;
            background: #fafbfc; font-size: 13px;
            display: flex; align-items: center; gap: 8px;
            list-style: none; user-select: none;
            transition: background 0.15s;
        }}
        .tb-frame-summary::-webkit-details-marker {{ display: none; }}
        .tb-frame-summary::before {{
            content: '\\25B6'; font-size: 9px; color: #999;
            transition: transform 0.2s; flex-shrink: 0;
        }}
        .tb-frame[open] > .tb-frame-summary::before {{
            transform: rotate(90deg);
        }}
        .tb-frame-summary:hover {{ background: #f0f4f8; }}

        .tb-frame-num {{
            background: #e5e7eb; color: #666; font-size: 11px;
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
            font-family: "SF Mono", Menlo, monospace;
        }}
        .tb-frame:last-of-type .tb-frame-num {{
            background: #fee2e2; color: #dc2626;
        }}
        .tb-module {{ color: #2563eb; font-weight: 600; }}
        .tb-separator {{ color: #ccc; }}
        .tb-lineno {{ color: #888; font-family: "SF Mono", Menlo, monospace; font-size: 12px; }}
        .tb-func {{ color: #7c3aed; font-weight: 500; }}
        .tb-func::before {{ content: 'in '; color: #999; font-weight: 400; }}
        .tb-hash {{
            color: #9ca3af; font-family: "SF Mono", Menlo, monospace;
            font-size: 10px; background: #f3f4f6; padding: 1px 5px;
            border-radius: 3px;
        }}
        .tb-locals-badge {{
            background: #dbeafe; color: #2563eb; font-size: 10px;
            padding: 1px 6px; border-radius: 10px; font-weight: 600;
            margin-left: auto;
        }}

        /* --- Frame body --- */
        .tb-frame-body {{ padding: 12px 16px 16px; background: white; }}
        .tb-filename {{
            color: #9ca3af; font-size: 11px; margin-bottom: 8px;
            word-break: break-all; font-family: "SF Mono", Menlo, monospace;
        }}
        .tb-code {{
            background: #1e293b; color: #e2e8f0; padding: 12px 16px;
            border-radius: 6px; font-family: "SF Mono", Menlo, monospace;
            font-size: 13px; overflow-x: auto; line-height: 1.5;
            margin-bottom: 8px;
        }}

        /* --- Locals --- */
        .tb-locals {{
            margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 6px;
            overflow: hidden;
        }}
        .tb-locals-header {{
            padding: 8px 12px; background: #f8fafc; cursor: pointer;
            font-size: 12px; color: #666; font-weight: 600;
            display: flex; align-items: center; gap: 6px;
            user-select: none; transition: background 0.15s;
        }}
        .tb-locals-header:hover {{ background: #f0f4f8; }}
        .tb-locals-toggle {{
            font-size: 10px; transition: transform 0.2s;
            display: inline-block;
        }}
        .tb-locals.expanded .tb-locals-toggle {{ transform: rotate(90deg); }}
        .tb-locals-table {{
            width: 100%; border-collapse: collapse;
            display: none; font-size: 12px;
        }}
        .tb-locals.expanded .tb-locals-table {{ display: table; }}
        .tb-locals-table th {{
            text-align: left; padding: 6px 12px; background: #f1f5f9;
            font-size: 11px; color: #666; text-transform: uppercase;
            letter-spacing: 0.3px; border-bottom: 1px solid #e5e7eb;
        }}
        .tb-locals-table td {{
            padding: 5px 12px; border-bottom: 1px solid #f1f5f9;
            vertical-align: top;
        }}
        .tb-locals-table tr:last-child td {{ border-bottom: none; }}
        .tb-locals-table tr:hover {{ background: #f8fafc; }}
        .loc-name {{
            font-family: "SF Mono", Menlo, monospace; font-weight: 600;
            color: #334155; white-space: nowrap; width: 1%;
        }}
        .loc-value {{
            font-family: "SF Mono", Menlo, monospace; color: #555;
            word-break: break-all; max-width: 0;
        }}
        .loc-value.special-value {{ color: #9ca3af; font-style: italic; }}

        /* --- Error message --- */
        .tb-error-message {{
            background: #fef2f2; color: #dc2626; padding: 14px 18px;
            border-radius: 8px; font-family: "SF Mono", Menlo, monospace;
            font-size: 14px; font-weight: 600; margin-top: 12px;
            border: 1px solid #fecaca; line-height: 1.5;
        }}
        .traceback-plain {{
            font-family: "SF Mono", Menlo, monospace; font-size: 13px;
            white-space: pre-wrap; background: #1e293b; color: #e2e8f0;
            padding: 16px; border-radius: 8px;
        }}
        .no-traceback {{ color: #888; font-style: italic; }}

        /* --- Header row --- */
        .error-header-row {{
            display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
        }}
        .ask-sourcerer-btn {{
            padding: 10px 20px; border: none; border-radius: 8px;
            background: #7c3aed; color: white; font-size: 14px;
            font-weight: 600; cursor: pointer; white-space: nowrap;
            transition: background 0.15s;
        }}
        .ask-sourcerer-btn:hover {{ background: #6d28d9; }}
        .ask-sourcerer-btn:disabled {{ background: #a78bfa; cursor: wait; }}

        /* --- Sourcerer result --- */
        .sourcerer-result {{
            background: white; border-radius: 12px; padding: 24px;
            margin-top: 16px; border-left: 5px solid #7c3aed;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            line-height: 1.6; font-size: 14px;
        }}
        .sourcerer-result h3 {{ color: #7c3aed; margin-bottom: 12px; }}
        .sourcerer-result pre {{
            background: #1e293b; color: #e2e8f0; padding: 12px 16px;
            border-radius: 6px; font-size: 13px; overflow-x: auto;
            margin: 8px 0;
        }}
        .sourcerer-error {{ color: #dc2626; }}
    </style>
</head>
<body>
    {body}
    <script>
    function expandAll() {{
        document.querySelectorAll('.tb-frame').forEach(function(d){{ d.open = true; }});
        document.querySelectorAll('.tb-locals').forEach(function(d){{ d.classList.add('expanded'); }});
    }}
    function collapseAll() {{
        document.querySelectorAll('.tb-frame').forEach(function(d){{ d.open = false; }});
        document.querySelectorAll('.tb-locals').forEach(function(d){{ d.classList.remove('expanded'); }});
    }}
    var SOURCERER_URL = '{sourcerer_url}';
    var SOURCERER_TOKEN = '{sourcerer_token}';
    var TRACEBACK_XML = {traceback_xml_json};
    function askSourcerer() {{
        var btn = document.getElementById('ask-sourcerer-btn');
        var resultDiv = document.getElementById('sourcerer-result');
        if (!SOURCERER_URL) return;
        btn.disabled = true;
        btn.textContent = 'Asking...';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<h3>Sourcerer</h3><p>Analyzing...</p>';
        fetch(SOURCERER_URL, {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + SOURCERER_TOKEN
            }},
            body: JSON.stringify({{
                method: 'tools/call',
                params: {{
                    name: 'err_explain_error',
                    arguments: {{ traceback_xml: TRACEBACK_XML }}
                }}
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            var text = '';
            if (data.result && data.result.content) {{
                data.result.content.forEach(function(c) {{
                    if (c.type === 'text') text += c.text;
                }});
            }} else if (data.error) {{
                text = '<span class="sourcerer-error">' + data.error.message + '</span>';
            }} else {{
                text = JSON.stringify(data, null, 2);
            }}
            resultDiv.innerHTML = '<h3>Sourcerer Analysis</h3><div>' + text + '</div>';
            btn.textContent = 'Ask Sourcerer';
            btn.disabled = false;
        }})
        .catch(function(err) {{
            resultDiv.innerHTML = '<h3>Sourcerer</h3><p class="sourcerer-error">Request failed: ' + err.message + '</p>';
            btn.textContent = 'Ask Sourcerer';
            btn.disabled = false;
        }});
    }}
    </script>
</body>
</html>'''.format(title=title, body=body,
                   sourcerer_url=sourcerer_url,
                   sourcerer_token=sourcerer_token,
                   traceback_xml_json=traceback_xml_json)
