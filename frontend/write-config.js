const fs = require("fs");
const path = require("path");

const apiBase = (process.env.API_BASE_URL || "").replace(/\/+$/, "");
const output = `window.API_BASE_URL = ${JSON.stringify(apiBase)};\n`;

fs.writeFileSync(path.join(__dirname, "config.js"), output);
console.log("Wrote frontend API configuration.");
