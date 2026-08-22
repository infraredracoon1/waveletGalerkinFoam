#!/usr/bin/env node
// Zero-dependency, conservative optimizer for the telemetry dashboard's single
// index.html: strips HTML comments and collapses blank lines/trailing
// whitespace. Deliberately does NOT touch the inline <script>/<style> bodies
// beyond that, to avoid the real risk of a naive minifier breaking JS syntax
// (ASI, template literals, etc.) for a page that's already only ~15KB.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const [, , srcPath, outPath] = process.argv;
if (!srcPath || !outPath) {
  console.error("usage: optimize-frontend.mjs <src.html> <out.html>");
  process.exit(1);
}

const before = readFileSync(srcPath, "utf8");
const optimized = before
  .replace(/<!--(?!\[if)[\s\S]*?-->/g, "") // strip HTML comments (keep IE conditionals, moot here, just safe practice)
  .split("\n")
  .map((line) => line.replace(/[ \t]+$/g, ""))
  .join("\n")
  .replace(/\n{3,}/g, "\n\n");

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, optimized);

const pct = (100 * (1 - optimized.length / before.length)).toFixed(1);
console.log(`optimized ${srcPath} -> ${outPath}: ${before.length}B -> ${optimized.length}B (-${pct}%)`);
