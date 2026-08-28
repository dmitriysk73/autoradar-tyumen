from __future__ import annotations
from playwright.async_api import async_playwright

class Browser:
    def __init__(self, headless=True):
        self.headless=headless
        self.pw=None
        self.browser=None
        self.ctx=None

    async def __aenter__(self):
        self.pw=await async_playwright().start()
        self.browser=await self.pw.chromium.launch(headless=self.headless)
        self.ctx=await self.browser.new_context(
            locale="ru-RU",
            viewport={"width":1440,"height":1200},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"
        )
        return self

    async def __aexit__(self,*args):
        if self.ctx: await self.ctx.close()
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()

    async def html(self,url,timeout=35000,scrolls=0):
        p=await self.ctx.new_page()
        try:
            await p.goto(url,wait_until="domcontentloaded",timeout=timeout)
            try: await p.wait_for_load_state("networkidle",timeout=8000)
            except: pass
            for _ in range(scrolls):
                await p.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await p.wait_for_timeout(700)
            return await p.content(), await p.url
        finally:
            await p.close()
