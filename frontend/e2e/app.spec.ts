import { expect, test, type Page } from '@playwright/test'

const routes = [
  '/',
  '/identify',
  '/explore',
  '/nearby',
  '/plan',
  '/plan/route?hours=6&mode=walk',
  '/monument/taj-mahal',
  '/monument/taj-mahal/related',
  '/connections',
  '/kit',
]

const tile = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eadbc0"/><path d="M0 80h256M0 176h256M80 0v256M176 0v256" stroke="#c8b594" stroke-width="2"/></svg>'

async function prepare(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
  })
  await page.route(/tile\.openstreetmap\.org/, (route) => route.fulfill({ body: tile, contentType: 'image/svg+xml' }))
  await page.route(/\/_next\/image\?/, (route) => route.fulfill({ body: tile, contentType: 'image/svg+xml' }))
}

test.describe('all pages', () => {
  test.beforeEach(async ({ page }) => prepare(page))

  for (const path of routes) {
    test(`${path} renders without layout or media failures`, async ({ page }) => {
      const pageErrors: string[] = []
      page.on('pageerror', (error) => pageErrors.push(error.message))
      const response = await page.goto(path)

      expect(response?.status(), path).toBeLessThan(400)
      const main = page.locator('main:visible').first()
      await expect(main).toBeVisible()
      await expect.poll(() => main.evaluate((element) => {
        let current: Element | null = element
        while (current) {
          if (Number.parseFloat(getComputedStyle(current).opacity) === 0) return false
          current = current.parentElement
        }
        return true
      }), { message: `${path} content should not be hidden by an entrance animation` }).toBe(true)
      await expect(page.locator('h1').first()).toBeAttached()
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), { message: `${path} should not overflow horizontally` }).toBeLessThanOrEqual(1)
      await expect.poll(() => page.locator('img').evaluateAll((images) => images.filter((image) => {
        const candidate = image as HTMLImageElement
        if (candidate.getClientRects().length === 0) return false
        // Lazy images outside the viewport have correctly not started loading yet.
        const box = candidate.getBoundingClientRect()
        const onScreen = box.bottom > 0 && box.right > 0 && box.top < innerHeight && box.left < innerWidth
        if (!candidate.complete) return onScreen || candidate.loading !== 'lazy'
        return candidate.naturalWidth === 0
      }).map((image) => image.getAttribute('src'))), { message: `${path} should not contain broken images` }).toEqual([])
      expect(pageErrors).toEqual([])
    })
  }

  test('every monument card has a photo from Wikimedia Commons', async ({ page }) => {
    await page.goto('/explore')
    const cardImages = page.locator('a[href^="/monument/"] img')

    await expect(cardImages).toHaveCount(28)
    for (const image of await cardImages.all()) {
      await expect(image).toHaveAttribute('src', /(thumb|upload)\.wikimedia\.org(?:%2F|\/)wikipedia/i)
    }
  })

  test('home desktop header continues the page surface', async ({ page, isMobile }) => {
    test.skip(isMobile, 'The desktop navigation is hidden on mobile.')
    await page.goto('/')
    await expect(page.locator('.desktop-nav')).not.toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
  })

  test('home desktop steps stay equal width', async ({ page, isMobile }) => {
    test.skip(isMobile, 'The mobile steps intentionally use a single column.')
    await page.goto('/')
    const section = page.getByRole('heading', { name: 'How it works' }).locator('../..')
    const widths = await section.locator('ol > li > div:first-child').evaluateAll((cards) => cards.map((card) => Math.round(card.getBoundingClientRect().width)))
    expect(new Set(widths).size).toBe(1)
    const connectors = section.locator('ol > li > div:nth-child(2) svg')
    await expect(connectors).toHaveCount(2)
    for (const connector of await connectors.all()) await expect(connector).toHaveCSS('opacity', '1')
  })

  test('language stays synchronized across shared and page controls', async ({ page }) => {
    await page.goto('/explore')
    await page.getByRole('button', { name: 'Switch to Hindi' }).click()
    await expect(page.locator('html')).toHaveAttribute('lang', 'hi')
    await expect(page.getByRole('heading', { name: 'स्मारक', exact: true })).toBeVisible()

    await page.getByRole('link', { name: /अपना दिन बनाएं/ }).first().click()
    await expect(page.getByRole('heading', { name: 'अपना दिन बनाएं' }).first()).toBeVisible()
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('lang', 'hi')
  })

  test('primary navigation has current state and touch-sized targets', async ({ page }) => {
    await page.goto('/explore')
    const nav = page.getByRole('navigation', { name: 'Primary navigation' })
    await expect(nav.getByRole('link', { name: /Monuments/ })).toHaveAttribute('aria-current', 'page')
    const boxes = await nav.getByRole('link').evaluateAll((links) => links.filter((link) => {
      const style = getComputedStyle(link)
      return style.display !== 'none' && style.visibility !== 'hidden'
    }).map((link) => {
      const box = link.getBoundingClientRect()
      return { width: box.width, height: box.height }
    }))
    expect(boxes.length).toBeGreaterThan(0)
    for (const box of boxes) {
      expect(box.width).toBeGreaterThanOrEqual(48)
      expect(box.height).toBeGreaterThanOrEqual(48)
    }
  })

  test('unknown monument slugs show the branded 404 page', async ({ page }) => {
    const response = await page.goto('/monument/not-a-monument')
    expect(response?.status()).toBe(404)
    await expect(page.getByRole('heading', { name: 'This monument is not on the map' })).toBeVisible()
  })
})

test('the home page opens without a blocking introduction', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Stories in stone, found along the way.' })).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Raahein introduction' })).toHaveCount(0)
})
