const path = require('node:path');
const {inspect} = require('node:util');

// node:test reporter for CI: passing tests print nothing. Failures, stderr (which
// carries process warnings) and the final totals are the only output.
module.exports = async function* quietReporter(source) {
    for await (const {type, data} of source) {
        if (type === 'test:fail') {
            const error = data.details.error;
            // A parent only repeats the failure already reported by its subtest
            if (error.failureType === 'subtestsFailed') {
                continue;
            }
            const location = data.file ? `${path.relative(process.cwd(), data.file)}: ` : '';
            yield `✖ ${location}${data.name}\n${inspect(error.cause ?? error)}\n\n`;
        } else if (type === 'test:stderr') {
            yield data.message;
        } else if (type === 'test:diagnostic') {
            yield `${data.message}\n`;
        }
    }
};
