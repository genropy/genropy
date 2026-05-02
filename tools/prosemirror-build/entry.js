// State / plugins / selections.
import {
    EditorState,
    Plugin,
    PluginKey,
    Transaction,
    Selection,
    TextSelection,
    NodeSelection,
    AllSelection
} from "prosemirror-state";

// View, decorations.
import {
    EditorView,
    Decoration,
    DecorationSet
} from "prosemirror-view";

// Document model.
import {
    Schema,
    Node as PMNode,
    Mark,
    Fragment,
    Slice,
    NodeRange,
    DOMParser,
    DOMSerializer
} from "prosemirror-model";

// Transformations.
import {
    Transform,
    Step,
    ReplaceStep,
    AddMarkStep,
    RemoveMarkStep
} from "prosemirror-transform";

// High-level commands.
import {
    baseKeymap,
    chainCommands,
    toggleMark,
    setBlockType,
    wrapIn,
    lift,
    joinUp,
    joinDown,
    selectAll,
    deleteSelection,
    selectParentNode,
    newlineInCode,
    createParagraphNear,
    liftEmptyBlock,
    splitBlock,
    exitCode
} from "prosemirror-commands";

// Keymap helper.
import { keymap } from "prosemirror-keymap";

// Undo/redo.
import {
    history,
    undo,
    redo,
    undoDepth,
    redoDepth
} from "prosemirror-history";

// Input rules (typing-driven shortcuts: ## -> heading, > -> blockquote, ...).
import {
    inputRules,
    InputRule,
    textblockTypeInputRule,
    wrappingInputRule,
    emDash,
    ellipsis,
    smartQuotes,
    undoInputRule
} from "prosemirror-inputrules";

// Pre-built schemas.
import { schema as basicSchema } from "prosemirror-schema-basic";
import {
    addListNodes,
    orderedList,
    bulletList,
    listItem,
    splitListItem,
    liftListItem,
    sinkListItem
} from "prosemirror-schema-list";

// UI helpers.
import { dropCursor } from "prosemirror-dropcursor";
import { gapCursor } from "prosemirror-gapcursor";

// Compose a default schema that adds list nodes to the basic schema, so
// callers that want lists out-of-the-box can use `schemas.basicWithLists`
// directly. The two raw schemas are also exposed for callers that want to
// build their own.
const basicWithListsSchema = new Schema({
    nodes: addListNodes(basicSchema.spec.nodes, "paragraph block*", "block"),
    marks: basicSchema.spec.marks
});

window.ProseMirror = {
    // state
    EditorState,
    Plugin,
    PluginKey,
    Transaction,
    Selection,
    TextSelection,
    NodeSelection,
    AllSelection,
    // view
    EditorView,
    Decoration,
    DecorationSet,
    // model
    Schema,
    Node: PMNode,
    Mark,
    Fragment,
    Slice,
    NodeRange,
    DOMParser,
    DOMSerializer,
    // transform
    Transform,
    Step,
    ReplaceStep,
    AddMarkStep,
    RemoveMarkStep,
    // commands
    baseKeymap,
    chainCommands,
    toggleMark,
    setBlockType,
    wrapIn,
    lift,
    joinUp,
    joinDown,
    selectAll,
    deleteSelection,
    selectParentNode,
    newlineInCode,
    createParagraphNear,
    liftEmptyBlock,
    splitBlock,
    exitCode,
    // keymap
    keymap,
    // history
    history,
    undo,
    redo,
    undoDepth,
    redoDepth,
    // inputrules
    inputRules,
    InputRule,
    textblockTypeInputRule,
    wrappingInputRule,
    emDash,
    ellipsis,
    smartQuotes,
    undoInputRule,
    // list helpers
    addListNodes,
    orderedList,
    bulletList,
    listItem,
    splitListItem,
    liftListItem,
    sinkListItem,
    // ui
    dropCursor,
    gapCursor,
    // pre-built schemas
    schemas: {
        basic: basicSchema,
        basicWithLists: basicWithListsSchema
    }
};
