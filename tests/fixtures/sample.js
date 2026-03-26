// Sample JS file for AST parser tests

import { readFile } from 'fs';

function processData(data) {
    return data.map(item => item.value);
}

function formatOutput(result) {
    return JSON.stringify(result);
}
