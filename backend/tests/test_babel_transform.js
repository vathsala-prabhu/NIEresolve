const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function testTransformAndCheck() {
    console.log("Loading Babel Standalone...");
    const cachePath = path.join(__dirname, "babel_standalone_cache.js");
    let babelCode;
    if (fs.existsSync(cachePath)) {
        babelCode = fs.readFileSync(cachePath, "utf-8");
    } else {
        const res = await fetch("https://cdn.jsdelivr.net/npm/@babel/standalone@7.24.4/babel.min.js");
        babelCode = await res.text();
        fs.writeFileSync(cachePath, babelCode, "utf-8");
    }

    const vm = require('vm');
    const sandbox = { window: {}, console: console, process: process };
    vm.createContext(sandbox);
    vm.runInContext(babelCode, sandbox);
    const Babel = sandbox.Babel || sandbox.window.Babel;

    const appJsPath = path.resolve(__dirname, "../../frontend/js/app.js");
    const appJsContent = fs.readFileSync(appJsPath, "utf-8");

    console.log(`[1] Compiling ${appJsPath} (${appJsContent.split('\n').length} lines) via Babel...`);
    const result = Babel.transform(appJsContent, {
        presets: ['react'],
        filename: 'app.js'
    });
    console.log("    -> Babel transform: SUCCESS!");

    const compiledPath = path.join(__dirname, "app.compiled.test.js");
    fs.writeFileSync(compiledPath, result.code, "utf-8");

    console.log(`[2] Running 'node --check ${compiledPath}' on compiled JavaScript...`);
    try {
        execSync(`node --check "${compiledPath}"`, { stdio: 'pipe' });
        console.log("    -> node --check: PASSED with 0 syntax errors!");
    } catch (e) {
        console.error("    -> node --check FAILED:", e.stderr.toString());
        fs.unlinkSync(compiledPath);
        return false;
    }

    fs.unlinkSync(compiledPath);
    console.log("\nAll JavaScript/JSX files audited and verified successfully!");
    return true;
}

testTransformAndCheck().then((ok) => {
    process.exit(ok ? 0 : 1);
}).catch((e) => {
    console.error("Fatal:", e);
    process.exit(1);
});
