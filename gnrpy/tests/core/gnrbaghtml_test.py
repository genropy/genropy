from gnr.core.gnrbag import Bag
from gnr.core.gnrbaghtml import BagToHtml
from gnr.core.gnrhtml import GnrHtmlBuilder


LONG_TEXT = ('A reasonably long description that cannot possibly fit in a '
             'narrow grid column and therefore wraps over several lines '
             'when white space is normal')


def _print_instance(columns, rowData, **attrs):
    """Build a minimal BagToHtml ready to call calcRowHeight outside a full run."""
    instance = BagToHtml()
    instance.grid_columns = columns
    instance._gridsColumnsBag = Bag()
    instance.builder = GnrHtmlBuilder()
    instance.currRowDataNode = rowData
    instance.lineno = 0
    for k, v in attrs.items():
        setattr(instance, k, v)
    return instance


def _expected_height(instance, text, width_mm):
    font_name, font_size = instance.gridFontMetrics()
    rows = instance.builder.calcRowsNumber(text, width_mm=width_mm - instance.grid_cell_text_margin,
                                           font_name=font_name, font_size=font_size)
    return max(1, rows) * instance.grid_row_height


def test_calcRowHeight_flat_when_no_wrappable_columns():
    p = _print_instance([dict(field='a', mm_width=50), dict(field='b', mm_width=30)],
                        dict(a=LONG_TEXT, b='x'))
    assert p.calcRowHeight() == p.grid_row_height


def test_calcRowHeight_wrappable_column_grows():
    p = _print_instance([dict(field='descr', mm_width=40, white_space='normal'),
                         dict(field='qty', mm_width=20)],
                        dict(descr=LONG_TEXT, qty=5))
    height = p.calcRowHeight()
    assert height > p.grid_row_height
    assert height == _expected_height(p, LONG_TEXT, 40)


def test_calcRowHeight_short_text_stays_flat():
    p = _print_instance([dict(field='descr', mm_width=40, white_space='normal')],
                        dict(descr='short'))
    assert p.calcRowHeight() == p.grid_row_height


def test_calcRowHeight_explicit_newlines():
    p = _print_instance([dict(field='notes', mm_width=60, white_space='normal')],
                        dict(notes='one\ntwo\nthree'))
    assert p.calcRowHeight() == 3 * p.grid_row_height


def test_calcRowHeight_columns_without_field_stay_flat():
    p = _print_instance([dict(mm_width=50, name='custom', white_space='normal')],
                        dict(anything=LONG_TEXT))
    assert p.calcRowHeight() == p.grid_row_height


def test_calcRowHeight_hidden_column_ignored():
    p = _print_instance([dict(field='descr', mm_width=40, white_space='normal', hidden=True),
                         dict(field='qty', mm_width=20)],
                        dict(descr=LONG_TEXT, qty=5))
    assert p.calcRowHeight() == p.grid_row_height


def test_calcRowHeight_opt_out_flag():
    p = _print_instance([dict(field='descr', mm_width=40, white_space='normal')],
                        dict(descr=LONG_TEXT),
                        auto_row_height=False)
    assert p.calcRowHeight() == p.grid_row_height


def test_calcRowHeight_flex_column_uses_residual_width():
    p = _print_instance([dict(field='code', mm_width=30),
                         dict(field='descr', mm_width=0, white_space='normal')],
                        dict(code='X1', descr=LONG_TEXT),
                        page_width=210, page_margin_left=10, page_margin_right=10)
    columns = [node.attr for node in p.sheetColumnsBag(0)]
    cells = p._gridRowCells(columns, p.rowData)
    flex_width = p._gridFlexWidth(cells)
    assert flex_width > 30  # residual page width, much wider than the fixed column
    assert p.calcRowHeight() == _expected_height(p, LONG_TEXT, flex_width)


def test_calcRowHeight_max_across_sheets():
    p = _print_instance([dict(field='a', mm_width=50, sheet=0),
                         dict(field='descr', mm_width=40, white_space='normal', sheet=1)],
                        dict(a='x', descr=LONG_TEXT),
                        sheets_counter=2)
    assert p.calcRowHeight() == _expected_height(p, LONG_TEXT, 40)


def test_calcRowHeight_none_value_stays_flat():
    p = _print_instance([dict(field='descr', mm_width=40, white_space='normal')],
                        dict(descr=None))
    assert p.calcRowHeight() == p.grid_row_height


def test_gridFontMetrics_default_is_narrow_9pt():
    p = _print_instance([], dict())
    assert p.gridFontMetrics() == ('Helvetica-Narrow', 9.0)


def test_gridFontMetrics_follows_declared_font_family():
    p = _print_instance([], dict(), font_family='Courier New, monospace')
    assert p.gridFontMetrics() == ('Courier', 9.0)


def test_mainLayoutParameters_uses_declared_font_family():
    p = _print_instance([], dict(), font_family='Courier')
    assert p.mainLayoutParameters()['font_family'] == 'Courier'
    assert BagToHtml().mainLayoutParameters()['font_family'] == 'Arial Narrow'
