// Decision register: notes/bag-integration/bag-decision-register.md of
// genropy_meta, D05-D14.
// Accepted removals: see the standalone BREAKING_CHANGES.md and
// notes/bag-integration/javascript-bag-breaking-changes.md of genropy_meta.
// Do not add unexplained parity gaps.
const bag = ['__str__', 'asObjList', 'merge', 'pathsplit', 'backrefOk',
    'formula', 'defineSymbol', 'defineFormula', 'set_modified', 'doWithItem',
    '__str2__', 'asString', 'newNode', 'setParent', 'setParentNode', 'set',
    'runTrigger', 'onNodeTrigger'];
const node = ['backrefOk', 'toJSONString', 'doWithValue'];
const resolver = ['getAttr', 'setAttr', 'resolverDescription'];
module.exports = {
    classes: ['GnrBagFormula', 'GnrBagGetter'],
    members: {GnrBag: bag, GnrDomSource: bag, GnrBagNode: node,
        GnrDomSourceNode: node, GnrBagResolver: resolver, GnrBagCbResolver: resolver}
};
