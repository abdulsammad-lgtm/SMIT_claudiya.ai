import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://127.0.0.1:3001/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # --> Assertions to verify final state
        
        # --> Verify KPI metrics are displayed
        # Assert: The 'Americas' KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[1]/div[1]/span[1]").nth(0)).to_have_text("Americas", timeout=15000), "The 'Americas' KPI label is visible."
        # Assert: The 'EMEA' KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[2]/div[1]/span[1]").nth(0)).to_have_text("EMEA", timeout=15000), "The 'EMEA' KPI label is visible."
        # Assert: A KPI percentage value ('72') is displayed.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[4]/div[2]/div[3]/div[1]/div[3]/span").nth(0)).to_contain_text("72", timeout=15000), "A KPI percentage value ('72') is displayed."
        
        # --> Verify live threat activity is displayed
        # Assert: Live threat feed contains a transaction with status 'blocked'.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[1]/span").nth(0)).to_have_text("blocked", timeout=15000), "Live threat feed contains a transaction with status 'blocked'."
        # Assert: Live threat feed contains a transaction showing the amount '$129.40'.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[2]/div[2]/p/span").nth(0)).to_have_text("$129.40", timeout=15000), "Live threat feed contains a transaction showing the amount '$129.40'."
        # Assert: Live threat feed contains a transaction with status 'allowed'.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[7]/span").nth(0)).to_have_text("allowed", timeout=15000), "Live threat feed contains a transaction with status 'allowed'."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    