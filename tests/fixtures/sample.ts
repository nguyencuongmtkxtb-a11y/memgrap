// Sample TS file for AST parser tests

import { Injectable } from '@nestjs/common';

class DataProcessor {
    process(input: string): string {
        return input.trim();
    }
}

function transformData(data: any[]): any[] {
    return data.filter(Boolean);
}
