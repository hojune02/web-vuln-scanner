from playwright.sync_api import sync_playwright

class JSRenderer:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self.browser = None
        self.context = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        return self
    
    def __exit__(self,exc_type, exc_val, exc_tb):
        if self.context != None:
            self.context.close()
        if self.browser != None:
            self.browser.close()
        if self._playwright != None:
            self._playwright.stop()
    
    def render(self, url: str, wait_until: str = "networkidle") -> tuple[str, str]:
        """
        Navigate to the URL, wait for JS to load, and return:
          - page HTML
          - final URL after redirects
        """
        page = self.context.new_page()
        page.goto(url, wait_until=wait_until)
        html = page.content()
        final_url = page.url
        page.close()
        return html, final_url