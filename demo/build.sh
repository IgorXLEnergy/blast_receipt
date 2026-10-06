#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p demo/dist/static
cp demo/index.html demo/dist/index.html
cp demo/app.js demo/dist/static/demo.js
cp demo/data.json demo/dist/static/data.json
cp service/static/styles.css service/static/result.js demo/dist/static/
cat demo/styles.css >> demo/dist/static/styles.css
