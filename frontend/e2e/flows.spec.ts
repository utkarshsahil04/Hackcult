import { expect, test, type Page } from '@playwright/test'

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')

async function openIdentify(page: Page, response: object = { status: 'ok', candidates: [{ slug: 'taj-mahal', name: 'Taj Mahal', score: .99 }] }, httpStatus = 200) {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
    localStorage.setItem('raahein-language', 'en')
  })
  await page.route('**/api/recognition/identify', (route) => route.fulfill({
    status: httpStatus,
    contentType: 'application/json',
    body: JSON.stringify(response),
  }))
  await page.goto('/identify')
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
    await openIdentify(page, { code: 'RECOGNITION_UNAVAILABLE' }, 503)
    await expect(page.getByRole('heading', { name: 'Something went wrong on our side' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Browse monuments instead' })).toBeVisible()
  })

  test('uncertain recognition requires a candidate before continuing', async ({ page }) => {
    await openIdentify(page, { status: 'uncertain', candidates: [{ slug: 'taj-mahal', name: 'Taj Mahal', score: .4 }, { slug: 'agra-fort', name: 'Agra Fort', score: .3 }] })
    await expect(page.getByRole('heading', { name: "We’re not sure about this one" })).toBeVisible()
    const confirm = page.getByRole('button', { name: 'Yes, this one' })
    await expect(confirm).toBeDisabled()
    await page.getByRole('button', { name: /Taj Mahal/ }).click()
    await expect(confirm).toBeEnabled()
    await confirm.click()
    await expect(page).toHaveURL(/\/monument\/taj-mahal$/)
  })
})

const feasible = { is_feasible: true, status_message: '', solver_status: 'SUCCESS', is_validated: true, explanation: '', itinerary: { time_budget_min: 240, total_time_min: 130, total_travel_time_min: 10, total_travel_distance_m: 3000, stops: [{ monument_slug: 'red-fort', name: 'Red Fort', arrival_time_min: 0, visit_duration_min: 75, departure_time_min: 75 }, { monument_slug: 'india-gate', name: 'India Gate', arrival_time_min: 85, visit_duration_min: 25, departure_time_min: 110 }] } }
const stubPlan = (page: Page, respond: () => object) => page.route('**/api/tours/plan', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(respond()) }))

test('planner choices are carried into the generated route', async ({ page }) => {
  await stubPlan(page, () => feasible)
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
  await page.route('**/api/tours/plan', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(route.request().postDataJSON()?.preset === 'quick' ? feasible : { ...feasible, is_feasible: false }) }))
  await page.goto('/plan/route')
  await expect(page.getByRole('heading', { name: 'That’s too much for one day' })).toBeVisible()
  await page.getByRole('link', { name: 'Show best 6-hour route' }).click()
  await expect(page.getByRole('heading', { name: 'Your day, connected' })).toBeVisible()
})

test('a failed plan shows an error, never an invented route', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
  await page.route('**/api/tours/plan', (route) => route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
  await page.goto('/plan/route?hours=4')
  await expect(page.getByRole('heading', { name: 'We could not build your plan' })).toBeVisible()
})

test('a listed site says its story is pending instead of inventing one', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
  await page.goto('/monument/india-gate')
  await expect(page.getByTestId('story-pending')).toBeVisible()
})

test('a listed site asks the API for nothing it does not have', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
  const missing: string[] = []
  page.on('response', (response) => { if (response.status() === 404 && response.url().includes('/api/')) missing.push(response.url()) })
  await page.goto('/monument/india-gate')
  await expect(page.getByRole('heading', { name: 'Nearby monuments' })).toBeVisible()
  await page.goto('/monument/india-gate/related')
  await expect(page.getByRole('heading', { name: 'Near India Gate' })).toBeVisible()
  await expect(page.getByTestId('connection-graph').getByRole('link')).toHaveCount(6)
  expect(missing).toEqual([])
})

test('the 3D view shows the model for this monument and explains its parts', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('raahein-language', 'en'))
  await page.goto('/monument/lotus-temple')
  await page.getByRole('button', { name: '3D Architecture' }).click()
  const viewer = page.getByTestId('monument-3d')
  await expect(viewer.getByRole('button', { name: /Water feature/ })).toBeVisible({ timeout: 60_000 })
  await viewer.getByRole('button', { name: /Water feature/ }).click()
  await expect(viewer.getByText('Still water that cools the air')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Lotus Temple' })).toBeVisible()
})
