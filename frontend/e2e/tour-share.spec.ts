import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
})

test('a shared tour link keeps only valid stops and saves them', async ({ page }) => {
  await page.goto('/tour?stops=taj-mahal,not-a-real-id,red-fort,taj-mahal&name=Weekend')
  await expect(page.getByRole('heading', { level: 1, name: 'Weekend' })).toBeVisible()
  const stops = page.getByTestId('tour-stop')
  await expect(stops).toHaveCount(2)
  await expect(stops.nth(0)).toContainText('Taj Mahal')
  await expect(stops.nth(1)).toContainText('Red Fort')
  await page.getByRole('button', { name: 'Save to my tour' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Saved to your tour' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('raahein-tour'))).toBe('["taj-mahal","red-fort"]')
})

test('a shared tour link with no valid stops shows the empty state', async ({ page }) => {
  await page.goto('/tour?stops=nothing')
  await expect(page.getByRole('heading', { name: 'This tour has no stops' })).toBeVisible()
  await expect(page.getByRole('main').getByRole('link', { name: 'Explore monuments' })).toHaveAttribute('href', '/explore')
})
