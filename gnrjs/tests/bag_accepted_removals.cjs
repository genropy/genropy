// Decision register: docs/bag-decision-register.md, D05-D14.
// Accepted removals: see the standalone BREAKING_CHANGES.md and
// docs/javascript-bag-breaking-changes.md. Do not add unexplained parity gaps.
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
