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
})
