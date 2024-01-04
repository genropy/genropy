from gnr.core import gnrlog as gl

def test_formattermessage():
    res = gl.formatter_message("hello", use_color=False)
    assert res == "hello"

def test_ColoredFormatter(caplog):
    import logging
    import sys, os
    
    caplog.set_level(logging.DEBUG)

    fmt = gl.ColoredFormatter("%(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    logger = logging.getLogger("test1")
    logger.addHandler(handler)
    logger.log(msg="hello", level=logging.DEBUG)
    assert "hello" in caplog.messages

    
    gl.root_logger = None
    gl.enable_colored_logging(stream=open('/dev/pts/1', 'w'),
                              level=logging.DEBUG, reset_handlers=True)
    gl.root_logger.log(msg="hello2", level=logging.DEBUG)
    assert "hello" in caplog.messages

def test_logstyles():
    l = gl.log_styles()
    assert l['color_blue'] == '\033[94m'
    assert 'color_blue' in l
    assert 'style_underlined' in l
    assert 'nostyle' in l
