function loadScript(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Script load error for ${url}`));
        document.head.append(script);
    });
}

loadScript('https://cdn.jsdelivr.net/npm/diff@latest/dist/diff.min.js')
    .then(() => {
        var diffUtil = {
            /**
             * Calculates the difference between two texts.
             * @param {string} text1 - The first text to compare.
             * @param {string} text2 - The second text to compare.
             * @param {string} mode - The mode of output ('html' or 'object').
             * @returns {string|Array} - Returns the diff as HTML string or as an object array.
             */
            calculateDifference: function(text1, text2, mode = 'object') {
                if (!text1 || !text2) {
                    return null;
                }

                var diff = Diff.diffWords(text1, text2);

                if (mode === 'html') {
                    var diffHtml = diff.map(part => {
                        var color = part.added ? 'darkgreen' :
                                    part.removed ? 'red' : 'black';
                        var textDecoration = part.removed ? 'line-through' : 'none';
                        return `<span style="color: ${color}; text-decoration: ${textDecoration}">${part.value}</span>`;
                    }).join('');
                    return diffHtml;
                } else if (mode === 'object') {
                    var diffOutput = diff.map(part => {
                        return {
                            value: part.value,
                            added: part.added || false,
                            removed: part.removed || false
                        };
                    });
                    return diffOutput;
                } else {
                    throw new Error('Invalid mode. Use "html" or "object".');
                }
            }
        };

        // Assign diffUtil to a global context if necessary
        window.diffUtil = diffUtil;
    })
    .catch(error => {
        console.error(error);
    });