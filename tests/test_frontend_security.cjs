const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

test("database schema and query results are escaped before HTML rendering", () => {
  const schemaList = { innerHTML: "" };
  const document = {
    addEventListener() {},
    querySelector(selector) { return selector === "#schema-list" ? schemaList : null; },
    getElementById() { return null; },
  };
  const context = {
    document,
    localStorage: { getItem() { return null; }, setItem() {} },
    console,
    setTimeout,
    clearTimeout,
    requestAnimationFrame() {},
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync("frontend/js/app.js", "utf8"), context);
  vm.runInContext(`S.schema = {
    '<img src=x onerror=alert(1)>': {
      row_count: 1,
      columns: [{name: '<svg onload=alert(1)>', type: 'TEXT<script>'}]
    }
  }`, context);
  context.renderSchema();
  const renderedSchema = schemaList.innerHTML;
  assert.doesNotMatch(renderedSchema, /<img|<svg|<script/i);
  assert.match(renderedSchema, /&lt;img/);
  assert.match(renderedSchema, /&lt;svg/);

  const table = context.buildTable([{ value: "<script>alert(1)</script>" }], ["value"]);
  assert.doesNotMatch(table, /<script>/i);
  assert.match(table, /&lt;script&gt;/);
});
