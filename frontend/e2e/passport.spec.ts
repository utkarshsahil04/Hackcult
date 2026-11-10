import { expect, test } from '@playwright/test'

test('heritage passport shows collected and uncollected stamps', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
    localStorage.setItem('raahein-language', 'en')
    localStorage.setItem('raahein-journey', JSON.stringify({ name: '', visits: [{ id: 'taj-mahal', date: '2026-11-04' }] }))
  })
  await page.goto('/profile')
  const passport = page.getByTestId('passport')
  await expect(passport.getByRole('link', { name: 'Taj Mahal, collected 4 November 2026' })).toBeVisible()
  await expect(passport.getByTestId('passport-count')).toHaveText('1 of 28 stamps')
  await expect(passport.getByRole('link', { name: 'Agra Fort, not collected yet' })).toHaveAttribute('href', '/monument/agra-fort')
})
