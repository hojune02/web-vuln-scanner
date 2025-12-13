from collections import deque
from typing import Set, List, Dict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import HttpClient
from .js_renderer import JSRenderer


class DynamicCrawler:
    """
    SPA-friendly crawler:
    - Uses Playwright-rendered DOM (JSRenderer)
    - Keeps URL fragments (/#/route) because SPA routing lives there
    - Extracts href="#/..." routes and converts them into navigable URLs
    """

    def __init__(
        self,
        client: HttpClient,
        renderer: JSRenderer,
        max_depth: int = 2,
        max_pages: int = 100,
    ):
        self.client = client
        self.renderer = renderer
        self.max_depth = max_depth
        self.max_pages = max_pages

        self.visited: Set[str] = set()
        self.discovered: Dict[str, int] = {}  # url -> depth

    def _normalize_url(self, url: str) -> str:
        """
        For SPA crawling, we DO NOT strip fragments.
        We only normalize by removing trailing slash duplication.
        """
        # Keep fragment because /#/route is meaningful in SPAs
        return url.rstrip("/")

    def _href_to_absolute(self, href: str, current_url: str) -> str:
        """
        Convert SPA-style hrefs to absolute URLs we can navigate to.
        - "#/login" => "http://host:port/#/login"
        - "/#/login" => "http://host:port/#/login"
        - "/assets/x" => normal urljoin
        """
        href = href.strip()

        # Ignore pure anchors like "#section" but keep "#/route"
        if href.startswith("#") and not href.startswith("#/"):
            return ""

        # Convert "#/route" -> current page origin + "#/route"
        if href.startswith("#/"):
            base = current_url.split("#", 1)[0]  # "http://localhost:3000"
            return base + href  # "http://localhost:3000#/login" (works)

        # Normal absolute/relative URL
        return urljoin(current_url, href)

    def extract_links(self, html: str, current_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue

            if href.startswith("javascript:") or href.startswith("mailto:"):
                continue

            absolute = self._href_to_absolute(href, current_url)
            if not absolute:
                continue

            absolute = self._normalize_url(absolute)

            # Domain filter (still OK)
            if self.client.same_domain(absolute):
                links.append(absolute)

        # Optional: also support Angular routerLink
        for elem in soup.find_all(attrs={"routerlink": True}):
            router_path = elem.get("routerlink")
            if not router_path:
                continue
            absolute = urljoin(current_url.split("#", 1)[0], router_path.strip())
            absolute = self._normalize_url(absolute)
            if self.client.same_domain(absolute):
                links.append(absolute)

        # Deduplicate
        return sorted(set(links))

    def crawl(self, start_url: str) -> List[str]:
        queue = deque()
        start_url = self._normalize_url(start_url)

        queue.append((start_url, 0))
        self.discovered[start_url] = 0

        while queue and len(self.visited) < self.max_pages:
            url, depth = queue.popleft()

            if url in self.visited:
                continue
            if depth > self.max_depth:
                continue

            print(f"[DynCrawl] Depth={depth} URL={url}")
            self.visited.add(url)

            # ✅ Use Playwright renderer, not requests
            try:
                html, final_url = self.renderer.render(url)
            except Exception as e:
                print(f"[DynCrawl] Render failed for {url}: {e}")
                continue

            final_url = self._normalize_url(final_url)

            links = self.extract_links(html, final_url)

            for link in links:
                if link not in self.visited and link not in self.discovered:
                    next_depth = depth + 1
                    if next_depth <= self.max_depth:
                        self.discovered[link] = next_depth
                        queue.append((link, next_depth))

        return list(self.visited)
