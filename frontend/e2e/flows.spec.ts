import { expect, test, type Page } from '@playwright/test'

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')

async function openIdentify(page: Page, query = '') {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
    localStorage.setItem('raahein-language', 'en')
  })
  await page.route('**/api/recognition/identify', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ status: 'ok', candidates: [{ slug: 'taj-mahal', name: 'Taj Mahal', score: .99 }] }),
  }))
  await page.goto(`/identify${query}`)
  await page.locator('input[type="file"]').first().setInputFiles({ name: 'monument.png', mimeType: 'image/png', buffer: png })
}

test('photo identification opens the matched monument story', async ({ page }) => {
  await openIdentify(page)
  await expect(page.getByRole('heading', { name: 'Taj Mahal' })).toBeVisible()
  await page.getByRole('link', { name: 'Read the story' }).click()
  await expect(page).toHaveURL(/\/monument\/taj-mahal$/)
  await expect(page.getByRole('heading', { name: 'Taj Mahal' }).first()).toBeVisible()
})

test.describe('desktop recovery states', () => {
  test.skip(({ isMobile }) => isMobile, 'State variations are covered once; the primary flow runs on both viewports.')

  test('recognition error offers retry and browse recovery', async ({ page }) => {
    await openIdentify(page, '?mock=error')
    await expect(page.getByRole('heading', { name: 'Something went wrong on our side' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Browse monuments instead' })).toBeVisible()
  })

  test('uncertain recognition requires a candidate before continuing', async ({ page }) => {
    await openIdentify(page, '?mock=uncertain')
    await expect(page.getByRole('heading', { name: "We’re not sure about this one" })).toBeVisible()
    const confirm = page.getByRole('button', { name: 'Yes, this one' })
    await expect(confirm).toBeDisabled()
    await page.getByRole('button', { name: /Taj Mahal/ }).click()
    await expect(confirm).toBeEnabled()
    await confirm.click()
    await expect(page).toHaveURL(/\/monument\/taj-mahal$/)
  })
})

test('planner choices are carried into the generated route', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
    localStorage.setItem('raahein-language', 'en')
  })
  await page.goto('/plan')
  const hours = page.getByLabel('Time available')
  await hours.focus()
  await hours.press('Home')
  await hours.press('ArrowRight')
  await hours.press('ArrowRight')
  await page.getByRole('button', { name: 'Architecture' }).click()
  await page.getByRole('button', { name: 'Auto or taxi' }).click()
  await page.getByRole('link', { name: 'Build my route' }).click()

  await expect(page).toHaveURL(/hours=4/)
  await expect(page).toHaveURL(/mode=auto/)
  await expect(page).toHaveURL(/interests=architecture/)
  await expect(page.getByRole('heading', { name: 'Your day, connected' })).toBeVisible()
  await expect(page.getByText('4 hours', { exact: true })).toBeVisible()
  await expect(page.getByText('Auto or taxi', { exact: true })).toBeVisible()
})

test('impossible route recovery actions lead to usable plans', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Recovery behavior is viewport independent.')
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
  await page.goto('/plan/route?mock=impossible')
  await expect(page.getByRole('heading', { name: 'That’s too much for one day' })).toBeVisible()
  await page.getByRole('link', { name: 'Show best 6-hour route' }).click()
  await expect(page.getByRole('heading', { name: 'Your day, connected' })).toBeVisible()
})
