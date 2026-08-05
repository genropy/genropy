import os
import sys
import hashlib
import linecache
import json

from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrbag import Bag


def _is_library_frame(filename):
    if filename.startswith('<'):
        return True
    _library_markers = (
        os.sep + 'site-packages' + os.sep,
        os.sep + 'lib' + os.sep + 'python',
        os.sep + 'Lib' + os.sep,
    )
    for marker in _library_markers:
        if marker in filename:
            return True
    return False

def tracebackBag(limit=None, full_stack=False):
    result = Bag()
    if limit is None:
        if hasattr(sys, 'tracebacklimit'):
            limit = sys.tracebacklimit
    n = 0
    hash_cache = {}
    tb = sys.exc_info()[2]
    frames = []
    last_own_idx = 0
    while tb is not None and (limit is None or n < limit):
        tb_bag = Bag()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        co = f.f_code
        filename = co.co_filename
        name = co.co_name
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno)
        if line: line = line.strip()
        else: line = None
        if filename not in hash_cache:
            try:
                with open(filename, 'rb') as fh:
                    hash_cache[filename] = hashlib.sha256(fh.read()).hexdigest()[:12]
            except Exception:
                hash_cache[filename] = None
        tb_bag['module'] = os.path.basename(os.path.splitext(filename)[0])
        tb_bag['filename'] = filename
        tb_bag['file_hash'] = hash_cache[filename]
        tb_bag['lineno'] = lineno
        tb_bag['name'] = name
        tb_bag['line'] = line
        loc = Bag()
        for k,v in list(f.f_locals.items()):
            try:
                if isinstance(v,GnrStructData):
                    v = '*STRUCTURE*'
                elif isinstance(v,Bag):
                    v = '*BAG*'
                elif isinstance(v,(dict,list,tuple)):

                    json.dumps(v)
                loc[k] = v
            except Exception:
                loc[k] = '*UNSERIALIZABLE* %s' %v.__class__
        tb_bag['locals'] = loc
        label = '%s method %s line %s' % (tb_bag['module'], name, lineno)
        frames.append((label, tb_bag, filename))
        if not _is_library_frame(filename):
            last_own_idx = n
        tb = tb.tb_next
        n = n + 1
    if not full_stack:
        frames = frames[:last_own_idx + 1]
    for label, tb_bag, _filename in frames:
        result[label] = tb_bag
    return Bag(root=result)
