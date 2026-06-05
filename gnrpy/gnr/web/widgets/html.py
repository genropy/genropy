"""GenroPy HTML widgets — standard HTML elements available on GnrDomSrc.

Formal documentation of the HTML namespace widgets.
These methods are generated at runtime via __getattr__ -> child(tag, **kwargs).
"""
from genro_bag.builder import element


class HtmlWidgets:
    """Mixin documenting standard HTML elements and GenroPy HTML extensions."""

    # --- Layout ---

    @element
    def html(self, **kwargs):
        """HTML root element."""
        ...

    @element
    def head(self, **kwargs):
        """HTML head element."""
        ...

    @element
    def body(self, **kwargs):
        """HTML body element."""
        ...

    @element
    def div(self, **kwargs):
        """HTML div container element."""
        ...

    @element
    def span(self, **kwargs):
        """HTML inline span element."""
        ...

    @element
    def br(self, **kwargs):
        """HTML line break element."""
        ...

    @element
    def hr(self, **kwargs):
        """HTML horizontal rule element."""
        ...

    @element
    def blockquote(self, **kwargs):
        """HTML block quotation element."""
        ...

    @element
    def pre(self, **kwargs):
        """HTML preformatted text element."""
        ...

    @element
    def iframe(self, **kwargs):
        """HTML inline frame element."""
        ...

    @element
    def frame(self, **kwargs):
        """HTML frame element."""
        ...

    @element
    def frameset(self, **kwargs):
        """HTML frameset element."""
        ...

    @element
    def noframes(self, **kwargs):
        """HTML noframes fallback element."""
        ...

    @element
    def fieldset(self, **kwargs):
        """HTML fieldset grouping element."""
        ...

    @element
    def legend(self, **kwargs):
        """HTML legend element for fieldset."""
        ...

    # --- Text ---

    @element
    def h1(self, **kwargs):
        """HTML heading level 1."""
        ...

    @element
    def h2(self, **kwargs):
        """HTML heading level 2."""
        ...

    @element
    def h3(self, **kwargs):
        """HTML heading level 3."""
        ...

    @element
    def h4(self, **kwargs):
        """HTML heading level 4."""
        ...

    @element
    def h5(self, **kwargs):
        """HTML heading level 5."""
        ...

    @element
    def h6(self, **kwargs):
        """HTML heading level 6."""
        ...

    @element
    def p(self, **kwargs):
        """HTML paragraph element."""
        ...

    @element
    def a(self, **kwargs):
        """HTML anchor (link) element."""
        ...

    @element
    def b(self, **kwargs):
        """HTML bold text element."""
        ...

    @element
    def i(self, **kwargs):
        """HTML italic text element."""
        ...

    @element
    def em(self, **kwargs):
        """HTML emphasis element."""
        ...

    @element
    def strong(self, **kwargs):
        """HTML strong importance element."""
        ...

    @element
    def small(self, **kwargs):
        """HTML small text element."""
        ...

    @element
    def big(self, **kwargs):
        """HTML big text element."""
        ...

    @element
    def sub(self, **kwargs):
        """HTML subscript element."""
        ...

    @element
    def sup(self, **kwargs):
        """HTML superscript element."""
        ...

    @element
    def code(self, **kwargs):
        """HTML inline code element."""
        ...

    @element
    def kbd(self, **kwargs):
        """HTML keyboard input element."""
        ...

    @element
    def samp(self, **kwargs):
        """HTML sample output element."""
        ...

    @element
    def var(self, **kwargs):
        """HTML variable element."""
        ...

    @element
    def tt(self, **kwargs):
        """HTML teletype text element."""
        ...

    @element
    def cite(self, **kwargs):
        """HTML citation element."""
        ...

    @element
    def q(self, **kwargs):
        """HTML short inline quotation element."""
        ...

    @element
    def abbr(self, **kwargs):
        """HTML abbreviation element."""
        ...

    @element
    def acronym(self, **kwargs):
        """HTML acronym element."""
        ...

    @element
    def dfn(self, **kwargs):
        """HTML definition term element."""
        ...

    @element
    def address(self, **kwargs):
        """HTML contact address element."""
        ...

    @element
    def bdo(self, **kwargs):
        """HTML bidirectional override element."""
        ...

    @element
    def ins(self, **kwargs):
        """HTML inserted text element."""
        ...

    # NOTE: 'del' is a Python keyword; the element is available via child('del', **kwargs).

    # --- Lists ---

    @element
    def ul(self, **kwargs):
        """HTML unordered list element."""
        ...

    @element
    def ol(self, **kwargs):
        """HTML ordered list element."""
        ...

    @element
    def li(self, **kwargs):
        """HTML list item element."""
        ...

    @element
    def dl(self, **kwargs):
        """HTML description list element."""
        ...

    @element
    def dt(self, **kwargs):
        """HTML description term element."""
        ...

    @element
    def dd(self, **kwargs):
        """HTML description details element."""
        ...

    # --- Forms ---

    @element
    def button(self, **kwargs):
        """HTML button element."""
        ...

    @element
    def input(self, **kwargs):
        """HTML input element."""
        ...

    @element
    def textarea(self, **kwargs):
        """HTML textarea element."""
        ...

    @element
    def select(self, **kwargs):
        """HTML select dropdown element."""
        ...

    @element
    def option(self, **kwargs):
        """HTML option element for select."""
        ...

    @element
    def optgroup(self, **kwargs):
        """HTML option group element."""
        ...

    @element
    def label(self, **kwargs):
        """HTML label element for form controls."""
        ...

    # --- Tables ---

    @element
    def table(self, **kwargs):
        """HTML table element."""
        ...

    @element
    def caption(self, **kwargs):
        """HTML table caption element."""
        ...

    @element
    def thead(self, **kwargs):
        """HTML table head section."""
        ...

    @element
    def tbody(self, **kwargs):
        """HTML table body section."""
        ...

    @element
    def tfoot(self, **kwargs):
        """HTML table foot section."""
        ...

    @element
    def tr(self, **kwargs):
        """HTML table row element."""
        ...

    @element
    def th(self, **kwargs):
        """HTML table header cell element."""
        ...

    @element
    def td(self, **kwargs):
        """HTML table data cell element."""
        ...

    @element
    def col(self, **kwargs):
        """HTML column properties element."""
        ...

    @element
    def colgroup(self, **kwargs):
        """HTML column group element."""
        ...

    # --- Media ---

    @element
    def img(self, **kwargs):
        """HTML image element."""
        ...

    @element
    def audio(self, **kwargs):
        """HTML audio playback element."""
        ...

    @element
    def video(self, **kwargs):
        """HTML video playback element."""
        ...

    @element
    def canvas(self, **kwargs):
        """HTML canvas drawing element."""
        ...

    @element
    def embed(self, **kwargs):
        """HTML embed element for external content."""
        ...

    @element
    def object(self, **kwargs):
        """HTML embedded object element."""
        ...

    @element
    def param(self, **kwargs):
        """HTML parameter element for object."""
        ...

    @element
    def map(self, **kwargs):
        """HTML image map element."""
        ...

    @element
    def area(self, **kwargs):
        """HTML image map area element."""
        ...

    # --- Head elements ---

    @element
    def title(self, **kwargs):
        """HTML document title element."""
        ...

    @element
    def base(self, **kwargs):
        """HTML base URL element."""
        ...

    @element
    def link(self, **kwargs):
        """HTML external resource link element."""
        ...

    @element
    def meta(self, **kwargs):
        """HTML metadata element."""
        ...

    @element
    def style(self, **kwargs):
        """HTML style element for CSS."""
        ...

    @element
    def noscript(self, **kwargs):
        """HTML noscript fallback element."""
        ...

    # --- GenroPy extensions ---

    @element
    def htmliframe(self, **kwargs):
        """GenroPy enhanced iframe with datastore integration and event bridging."""
        ...

    @element
    def flexbox(self, **kwargs):
        """GenroPy flexbox layout container with CSS flex properties support."""
        ...

    @element
    def gridbox(self, **kwargs):
        """GenroPy CSS grid layout container for two-dimensional grid arrangements."""
        ...

    @element
    def labledbox(self, **kwargs):
        """GenroPy labeled box — a container with a built-in label/title header."""
        ...
