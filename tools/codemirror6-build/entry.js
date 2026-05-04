import {EditorState, Compartment, StateField, StateEffect, RangeSet, RangeSetBuilder} from "@codemirror/state";
import {
    EditorView,
    keymap,
    lineNumbers,
    highlightActiveLine,
    highlightActiveLineGutter,
    drawSelection,
    dropCursor,
    rectangularSelection,
    crosshairCursor,
    highlightSpecialChars,
    Decoration,
    WidgetType,
    gutter,
    GutterMarker
} from "@codemirror/view";
import {
    defaultKeymap,
    history,
    historyKeymap,
    indentWithTab
} from "@codemirror/commands";
import {
    search,
    searchKeymap,
    highlightSelectionMatches,
    openSearchPanel,
    closeSearchPanel
} from "@codemirror/search";
import {
    indentOnInput,
    bracketMatching,
    foldGutter,
    foldKeymap,
    syntaxHighlighting,
    defaultHighlightStyle,
    HighlightStyle
} from "@codemirror/language";
import {sql} from "@codemirror/lang-sql";
import {python} from "@codemirror/lang-python";
import {javascript} from "@codemirror/lang-javascript";
import {css} from "@codemirror/lang-css";
import {html} from "@codemirror/lang-html";
import {xml} from "@codemirror/lang-xml";
import {json} from "@codemirror/lang-json";
import {markdown} from "@codemirror/lang-markdown";
import {yaml} from "@codemirror/lang-yaml";
import {oneDark} from "@codemirror/theme-one-dark";
import {
    amy,
    ayuLight,
    barf,
    bespin,
    birdsOfParadise,
    boysAndGirls,
    clouds,
    cobalt,
    coolGlow,
    dracula,
    espresso,
    noctisLilac,
    rosePineDawn,
    smoothy,
    solarizedLight,
    tomorrow
} from "thememirror";

// Theme for CM6 "tools" (search panel, tooltip, autocomplete, lint diagnostics).
// Themes from `thememirror` and `@codemirror/theme-one-dark` only style the
// editor frame (background, gutter, content, syntax). Tools live outside that
// scope, so we ship a dedicated tools theme that gets merged into every editor
// instance regardless of which inner theme is active.
const toolsTheme = EditorView.theme({
    "&.cm-editor": {
        borderRadius: "3px"
    },
    ".cm-panels": {
        borderColor: "rgba(127,127,127,0.25)"
    },
    ".cm-panels.cm-panels-bottom": {
        borderTop: "1px solid rgba(127,127,127,0.35)"
    },
    ".cm-panels.cm-panels-top": {
        borderBottom: "1px solid rgba(127,127,127,0.35)"
    },
    ".cm-panel.cm-search": {
        padding: "6px 8px",
        display: "flex",
        flexWrap: "wrap",
        gap: "4px",
        alignItems: "center",
        fontSize: "12px",
        fontFamily: "system-ui, -apple-system, sans-serif"
    },
    ".cm-panel.cm-search input[type=\"text\"]": {
        border: "1px solid rgba(127,127,127,0.4)",
        borderRadius: "3px",
        padding: "3px 6px",
        minWidth: "140px",
        fontSize: "12px",
        background: "rgba(255,255,255,0.05)",
        color: "inherit"
    },
    ".cm-panel.cm-search input[type=\"text\"]:focus": {
        outline: "none",
        borderColor: "#5a8dd6",
        boxShadow: "0 0 0 2px rgba(90,141,214,0.25)"
    },
    ".cm-panel.cm-search button": {
        border: "1px solid rgba(127,127,127,0.4)",
        borderRadius: "3px",
        padding: "3px 9px",
        fontSize: "12px",
        cursor: "pointer",
        background: "rgba(255,255,255,0.04)",
        color: "inherit"
    },
    ".cm-panel.cm-search button:hover": {
        borderColor: "#5a8dd6",
        background: "rgba(90,141,214,0.12)"
    },
    ".cm-panel.cm-search button[name=\"close\"]": {
        marginLeft: "auto",
        border: "none",
        background: "transparent",
        fontSize: "16px",
        lineHeight: "1",
        padding: "0 6px",
        opacity: "0.6"
    },
    ".cm-panel.cm-search button[name=\"close\"]:hover": {
        opacity: "1",
        background: "transparent"
    },
    ".cm-panel.cm-search label": {
        display: "inline-flex",
        alignItems: "center",
        gap: "3px",
        cursor: "pointer",
        opacity: "0.85"
    },
    ".cm-searchMatch": {
        backgroundColor: "rgba(255,200,60,0.4)",
        outline: "1px solid rgba(255,160,0,0.7)"
    },
    ".cm-searchMatch.cm-searchMatch-selected": {
        backgroundColor: "rgba(255,160,0,0.7)"
    },
    ".cm-tooltip": {
        border: "1px solid rgba(127,127,127,0.35)",
        borderRadius: "3px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
        fontSize: "12px",
        fontFamily: "system-ui, -apple-system, sans-serif"
    },
    ".cm-tooltip.cm-tooltip-autocomplete > ul": {
        fontFamily: "inherit",
        maxHeight: "220px"
    },
    ".cm-tooltip.cm-tooltip-autocomplete > ul > li": {
        padding: "3px 8px"
    },
    ".cm-tooltip.cm-tooltip-autocomplete > ul > li[aria-selected]": {
        background: "#2962ff",
        color: "#ffffff"
    },
    ".cm-tooltip .cm-completionLabel": {
        fontWeight: "500"
    },
    ".cm-tooltip .cm-completionDetail": {
        opacity: "0.7",
        fontStyle: "italic",
        marginLeft: "8px",
        fontSize: "11px"
    },
    ".cm-diagnostic": {
        padding: "4px 8px",
        borderLeft: "4px solid"
    },
    ".cm-diagnostic-error": {
        borderLeftColor: "#d9534f",
        backgroundColor: "rgba(217,83,79,0.10)"
    },
    ".cm-diagnostic-warning": {
        borderLeftColor: "#f0ad4e",
        backgroundColor: "rgba(240,173,78,0.10)"
    },
    ".cm-diagnostic-info": {
        borderLeftColor: "#5a8dd6",
        backgroundColor: "rgba(90,141,214,0.10)"
    },
    ".cm-placeholder": {
        opacity: "0.5",
        fontStyle: "italic"
    }
});

window.CodeMirror6 = {
    EditorState,
    EditorView,
    Compartment,
    StateField,
    StateEffect,
    RangeSet,
    RangeSetBuilder,
    Decoration,
    WidgetType,
    gutter,
    GutterMarker,
    keymap,
    lineNumbers,
    highlightActiveLine,
    highlightActiveLineGutter,
    drawSelection,
    dropCursor,
    rectangularSelection,
    crosshairCursor,
    highlightSpecialChars,
    defaultKeymap,
    history,
    historyKeymap,
    indentWithTab,
    search,
    searchKeymap,
    highlightSelectionMatches,
    openSearchPanel,
    closeSearchPanel,
    indentOnInput,
    bracketMatching,
    foldGutter,
    foldKeymap,
    syntaxHighlighting,
    defaultHighlightStyle,
    HighlightStyle,
    toolsTheme: toolsTheme,
    langs: {sql, python, javascript, css, html, xml, json, markdown, yaml},
    themes: {
        oneDark: oneDark,
        amy: amy,
        ayuLight: ayuLight,
        barf: barf,
        bespin: bespin,
        birdsOfParadise: birdsOfParadise,
        boysAndGirls: boysAndGirls,
        clouds: clouds,
        cobalt: cobalt,
        coolGlow: coolGlow,
        dracula: dracula,
        espresso: espresso,
        noctisLilac: noctisLilac,
        rosePineDawn: rosePineDawn,
        smoothy: smoothy,
        solarizedLight: solarizedLight,
        tomorrow: tomorrow
    }
};
