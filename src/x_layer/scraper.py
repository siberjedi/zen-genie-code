"""
Faz 6 — Playwright X scraper iskeleti (izole).
X_ENABLED=false ise no-op döner — trader etkilenmez.
"""
import os

X_ENABLED = os.getenv("X_ENABLED","false").lower()=="true"

async def scrape_search(query: str, limit: int=20):
    if not X_ENABLED:
        return []  # izole: kapalıyken trader çalışır
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page()
        await page.goto(f"https://x.com/search?q={query}&src=typed_query&f=live")
        await page.wait_for_timeout(3000)
        # TODO: tweet selector — X DOM'u sık değişir, selector'ları test et
        items=await page.query_selector_all("article")
        out=[]
        for el in items[:limit]:
            txt=await el.inner_text()
            out.append({"text": txt[:500]})
        await browser.close()
        return out
