import { test, expect, type Page } from '@playwright/test'
import path from 'path'

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../docs/screenshots')
const OM_API = 'http://127.0.0.1:8585/api/v1'

async function waitLoaded(page: Page) {
  await page.waitForSelector('.pg-loading', { state: 'detached', timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(600)
}

/** Return the id of the first table from the OpenMetadata API */
async function fetchFirstTableId(page: Page): Promise<string> {
  const res = await page.request.get(`${OM_API}/tables?limit=1`)
  const json = await res.json()
  const id: string = json?.data?.[0]?.id
  if (!id) throw new Error('No tables returned from OpenMetadata API')
  return id
}

/** Return the name of the first DatabaseService from the OpenMetadata API */
async function fetchFirstServiceName(page: Page): Promise<string> {
  const res = await page.request.get(`${OM_API}/services/databaseServices?limit=1`)
  const json = await res.json()
  const name: string = json?.data?.[0]?.name
  if (!name) throw new Error('No DatabaseServices returned from OpenMetadata API')
  return name
}

test.describe('UI screenshots', () => {
  test('home – ドメイン一覧', async ({ page }) => {
    await page.goto('/')
    await waitLoaded(page)

    await expect(page.locator('.domain-grid')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'home.png') })
  })

  test('domain – テーブル一覧', async ({ page }) => {
    await page.goto('/domain')
    await waitLoaded(page)

    await expect(page.locator('.tbl-grid, .no-data')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'tables.png') })
  })

  test('table detail – カラム', async ({ page }) => {
    const tableId = await fetchFirstTableId(page)
    await page.goto(`/table/${tableId}`)
    await waitLoaded(page)

    await expect(page.locator('.ov-name')).toBeVisible()
    await expect(page.locator('.ctbl')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'table_detail.png') })
  })

  test('table detail – Lineage', async ({ page }) => {
    const tableId = await fetchFirstTableId(page)
    await page.goto(`/table/${tableId}`)
    await waitLoaded(page)

    await page.locator('.tb', { hasText: 'Lineage' }).click()
    await page.waitForTimeout(1200)

    await expect(page.locator('.pane')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'lineage.png') })
  })

  test('table detail – Data Quality (鮮度チェック)', async ({ page }) => {
    // customers は freshness + quality テストが両方あるテーブルを狙う
    const res = await page.request.get(`${OM_API}/tables?limit=50&fields=name,fullyQualifiedName`)
    const json = await res.json()
    const customersTable = json?.data?.find((t: { name: string }) => t.name === 'customers')
      ?? json?.data?.[0]
    if (!customersTable) throw new Error('No tables found')

    await page.goto(`/table/${customersTable.id}`)
    await waitLoaded(page)

    await page.locator('.tb', { hasText: 'Data Quality' }).click()
    // DQ データのロードを待つ
    await page.waitForSelector('.freshness-card, .tc-item, .no-data', { timeout: 10000 })
    await page.waitForTimeout(400)

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'data_quality.png') })
  })

  test('systems – システムカタログ一覧', async ({ page }) => {
    await page.goto('/systems')
    await waitLoaded(page)

    await expect(page.locator('.svc-grid')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'systems.png') })
  })

  test('system detail – サービス詳細', async ({ page }) => {
    const svcName = await fetchFirstServiceName(page)
    await page.goto(`/system/${encodeURIComponent(svcName)}`)
    await waitLoaded(page)

    await expect(page.locator('.ov-name')).toBeVisible()
    await expect(page.locator('.svctbl')).toBeVisible()
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'system_detail.png') })
  })
})
