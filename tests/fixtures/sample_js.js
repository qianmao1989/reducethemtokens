import { readFile } from 'fs';
import path from 'path';

function parseConfig(filePath) {
    return JSON.parse(readFile(filePath));
}

const loadEnv = (name) => process.env[name];

class DataStore {
    constructor(config) {
        this.config = config;
    }

    get(key) {
        return this.config[key];
    }

    set(key, value) {
        this.config[key] = value;
    }
}

export function createStore(config) {
    return new DataStore(config);
}

export class Logger {
    log(msg) {
        console.log(msg);
    }
}
