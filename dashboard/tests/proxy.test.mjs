import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
// Strip only imports to exercise the real Vite config without starting services.
const source = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8')
const config = new Function('defineConfig', 'react', source.replace(/^import .*;\r?\n/gm, '').replace('export default ', 'return '))(v => v, () => ({}))
for (const [route, port] of [['/api/v1/machines',8002], ['/api/v1/timeseries',8002], ['/api/v1/summary/mill',8002], ['/api/v1/alerts/1/acknowledge',8003]]) {
  test(`routes ${route} to ${port}`, () => {
    const key = Object.keys(config.server.proxy).find(k => route.startsWith(k))
    assert.ok(key, `No proxy matches ${route}`)
    assert.equal(config.server.proxy[key].target, `http://localhost:${port}`)
  })
}
