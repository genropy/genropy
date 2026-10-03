"""GenroPy-specific serialization contracts for the native Bag adapter."""

import json
import os
from pathlib import Path
import subprocess
import sys


_GNRPY = Path(__file__).resolve().parents[2]


def test_genropy_js_rows_preserve_references_and_legacy_localization(tmp_path):
    config = tmp_path / "instanceconfig.xml"
    config.write_text(
        '<GenRoBag><experimental><bag implementation="genro-bag"/>'
        '</experimental></GenRoBag>'
    )
    code = r'''
import json
from gnr.core.gnrbag import Bag
from genro_bag import Bag as NativeBag
from gnr.web.gnrbagtransport import encode_envelope

class Handler:
    def rpc_ping(self):
        return "pong"

class Payload:
    pass

handler = Handler()
bag = Bag()
bag.set_item("title", "!!Hello", _attributes={
    "caption": "!!Caption",
    "action": handler.rpc_ping,
    "payload_cls": Payload,
    "nested": {"label": "!!Nested"},
})
bag.set_item("callback", handler.rpc_ping)
bag.set_item("branch", Bag({"child": "!!Child"}))
bag.set_item("nothing", None)
bag.set_item("prefixed_text", "::ordinary")
before_value = bag["title"]
before_attrs = dict(bag.get_node("title").attr)
seen = []

def translate(value):
    seen.append(value)
    return "translated:" + value

result = bag.to_genropy_js(translate)
assert Bag is NativeBag
assert result["rows"] == [
    ("", "title", None, "translated:!!Hello", {
        "caption": "translated:!!Caption",
        "action": "ping::RPC",
        "payload_cls": "__main__:Payload::CLS",
        "nested": {"label": "!!Nested"},
    }),
    ("", "callback", None, "ping::RPC", {}),
    ("", "branch", None, "::X", {}),
    ("branch", "child", None, "translated:!!Child", {}),
    ("", "nothing", None, "::NN", {}),
    ("", "prefixed_text", None, "translated:::ordinary", {}),
]
assert seen == ["!!Hello", "!!Caption", "!!Child", "::ordinary"]
assert bag["title"] == before_value
assert bag.get_node("title").attr == before_attrs
assert bag.get_node("title").attr["action"].__self__ is handler
assert bag.get_node("title").attr["action"].__func__ is Handler.rpc_ping
wire = encode_envelope(bag, translate)
assert isinstance(wire, bytes)
assert json.loads(wire.decode("utf-8")) == json.loads(json.dumps(result))
print(json.dumps(result))
'''
    env = os.environ.copy()
    env.update(
        GNR_INSTANCE_CONFIG=str(config),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONPATH=os.pathsep.join([str(_GNRPY), env.get("PYTHONPATH", "")]),
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["rows"][0][3] == "translated:!!Hello"
