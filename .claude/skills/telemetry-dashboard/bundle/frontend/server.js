// Zero-dependency static file server (no npm install required).
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.TELEMETRY_FRONTEND_PORT || 3000;
const ROOT = __dirname;
const TYPES = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css" };

const server = http.createServer((req, res) => {
  let reqPath = decodeURIComponent(req.url.split("?")[0]);
  if (reqPath === "/") reqPath = "/index.html";
  const filePath = path.join(ROOT, reqPath);
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not found");
      return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": TYPES[ext] || "application/octet-stream" });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`Telemetry frontend serving on http://localhost:${PORT}`);
});
