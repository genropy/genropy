const payment_data = {
    onLoading: function(data) {
        const nodes = data.getNodes();
        const gridBag = new gnr.GnrBag();
        let i = 0;
        const toRemove = [];
        for (const [k, node] of nodes.entries()) {
            if (node.label === 'PaymentDetail') {
                const val = node.getValue();
                if (val instanceof gnr.GnrBag) {
                    gridBag.setItem('r_' + i, val.deepCopy());
                } else {
                    gridBag.setItem('r_' + i, new gnr.GnrBag(val));
                }
                toRemove.push(k);
                i++;
            }
        }
        for (const idx of toRemove.reverse()) {
            data.delItem('#' + idx);
        }
        if (i > 0) {
            data.setItem('PaymentDetail', gridBag);
        }
    },

    onSaving: function(data, sourceBag) {
        const dettaglio = data.getItem('PaymentDetail');
        if (!dettaglio) {
            return;
        }
        data.delItem('PaymentDetail');
        const nodes = sourceBag.getNodes();
        for (let k = nodes.length - 1; k >= 0; k--) {
            if (nodes[k].label === 'PaymentDetail') {
                sourceBag.delItem('#' + k);
            }
        }
        for (const n of dettaglio.getNodes()) {
            const val = n.getValue();
            if (val instanceof gnr.GnrBag) {
                sourceBag.addItem('PaymentDetail', val.deepCopy());
            } else {
                sourceBag.addItem('PaymentDetail', new gnr.GnrBag(val));
            }
        }
    }
};
