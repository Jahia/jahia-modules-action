/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ 760:
/***/ ((__unused_webpack_module, exports) => {


Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.compact = void 0;
// One line, cut at a limit: the trace stays readable whatever the agent printed.
const compact = (value, limit = 300) => {
    const text = typeof value === 'string' ? value : JSON.stringify(value);
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- JSON.stringify(undefined) is undefined at runtime, whatever its declared type
    const joined = (text ?? '').split(/\s+/).filter(Boolean).join(' ');
    return joined.length <= limit ? joined : joined.slice(0, limit) + '…';
};
exports.compact = compact;


/***/ }),

/***/ 723:
/***/ ((__unused_webpack_module, exports, __nccwpck_require__) => {


Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.traceRun = void 0;
const compact_1 = __nccwpck_require__(760);
const contentBlocks = (event) => {
    const message = event.message;
    return Array.isArray(message?.content) ? message.content : [];
};
// A deterministic trace of everything the agent did (tool calls, messages, final result), and
// the figures of the summary row.
const traceRun = (events, key, exitCode) => {
    const lines = [`--- Agent trace (${key}) ---`];
    let result = null;
    for (const event of events) {
        if (event.type === 'system' && event.subtype === 'init') {
            lines.push(`[init] model=${String(event.model)} cwd=${String(event.cwd)}`);
        }
        else if (event.type === 'assistant') {
            for (const block of contentBlocks(event)) {
                if (block.type === 'text')
                    lines.push(`[say ] ${(0, compact_1.compact)(block.text ?? '')}`);
                else if (block.type === 'tool_use') {
                    lines.push(`[tool] ${String(block.name)} ${(0, compact_1.compact)(block.input ?? {})}`);
                }
            }
        }
        else if (event.type === 'result') {
            result = event;
        }
    }
    if (result === null) {
        lines.push(`[end ] no result event found, agent exit code ${exitCode}`);
        return {
            lines,
            result,
            outcome: 'no result (crash/kill)',
            turns: 'n/a',
            duration: 'n/a',
            cost: 'n/a',
        };
    }
    let outcome = typeof result.subtype === 'string' ? result.subtype : 'unknown';
    if (result.is_error === true)
        outcome = `error (${outcome})`;
    const turns = typeof result.num_turns === 'number' ? String(result.num_turns) : 'n/a';
    const duration = typeof result.duration_ms === 'number'
        ? `${String(Math.round(result.duration_ms / 1000))}s`
        : 'n/a';
    const cost = typeof result.total_cost_usd === 'number' ? result.total_cost_usd.toFixed(4) : 'n/a';
    lines.push(`[end ] ${outcome} turns=${turns} duration=${duration} cost=$${cost} exit=${exitCode}`);
    lines.push(`[result] ${(0, compact_1.compact)(result.result ?? '', 2000)}`);
    return { lines, result, outcome, turns, duration, cost };
};
exports.traceRun = traceRun;


/***/ }),

/***/ 24:
/***/ ((module) => {

module.exports = require("node:fs");

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __nccwpck_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		var threw = true;
/******/ 		try {
/******/ 			__webpack_modules__[moduleId](module, module.exports, __nccwpck_require__);
/******/ 			threw = false;
/******/ 		} finally {
/******/ 			if(threw) delete __webpack_module_cache__[moduleId];
/******/ 		}
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/compat */
/******/ 	
/******/ 	if (typeof __nccwpck_require__ !== 'undefined') __nccwpck_require__.ab = __dirname + "/";
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry need to be wrapped in an IIFE because it uses a non-standard name for the exports (exports).
(() => {
var exports = __webpack_exports__;

Object.defineProperty(exports, "__esModule", ({ value: true }));
const node_fs_1 = __nccwpck_require__(24);
const compact_1 = __nccwpck_require__(760);
const traceRun_1 = __nccwpck_require__(723);
// summarize-run entry point: prints the deterministic trace of one headless Claude Code run from
// its stream-json output, writes the final result event next to the stream file, and appends one
// row to the step summary. It always exits 0 — reporting must not mask the agent's own exit code.
const run = () => {
    const [streamPath = '', key = '', exitCode = ''] = process.argv.slice(2);
    const events = [];
    try {
        for (const line of (0, node_fs_1.readFileSync)(streamPath, 'utf8').split('\n')) {
            const trimmed = line.trim();
            if (!trimmed)
                continue;
            try {
                events.push(JSON.parse(trimmed));
            }
            catch {
                console.log(`[warn] unparseable stream line: ${(0, compact_1.compact)(trimmed, 120)}`);
            }
        }
    }
    catch (error) {
        console.log(`[warn] could not read stream file: ${String(error)}`);
    }
    const trace = (0, traceRun_1.traceRun)(events, key, exitCode);
    for (const line of trace.lines)
        console.log(line);
    if (trace.result !== null) {
        (0, node_fs_1.writeFileSync)(streamPath.replace('.stream.jsonl', '.result.json'), JSON.stringify(trace.result, null, 2));
    }
    const summaryPath = process.env.GITHUB_STEP_SUMMARY;
    if (summaryPath) {
        (0, node_fs_1.appendFileSync)(summaryPath, `| ${key} | ${trace.outcome} | ${trace.turns} | ${trace.duration} | ${trace.cost} | ${exitCode} |\n`);
    }
};
run();

})();

module.exports = __webpack_exports__;
/******/ })()
;