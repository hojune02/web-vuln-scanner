# core/crawler.py

from collections import deque
from typing import Set, List, Dict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import HttpClient


class Crawler:
    """
    Simple BFS crawler that stays within the same domain and tracks depth.
    """

    def __init__(self, client: HttpClient, max_depth: int = 2, max_pages: int = 100):
        self.client = client
        self.max_depth = max_depth
        self.max_pages = max_pages

        self.visited: Set[str] = set()
        self.discovered: Dict[str, int] = {}  # url -> depth

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL (strip fragments, etc).
        """
        parsed = urlparse(url)
        # Remove fragment (#something)
        cleaned = parsed._replace(fragment="")
        return cleaned.geturl()

    def extract_links(self, html: str, current_url: str) -> List[str]:
        """
        Extract all links from the HTML that are within the same domain.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            raw_href = a["href"].strip()

            # ignore javascript:, mailto:, etc.
            if raw_href.startswith("#"):
                continue
            if raw_href.startswith("javascript:"):
                continue
            if raw_href.startswith("mailto:"):
                continue

            absolute = urljoin(current_url, raw_href)
            absolute = self._normalize_url(absolute)

            if self.client.same_domain(absolute):
                links.append(absolute)

        return links

    def crawl(self, start_url: str) -> List[str]:
        """
        BFS crawl from start_url, up to max_depth and max_pages.
        Returns a list of all visited URLs.
        """
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

            print(f"[Crawl] Depth={depth} URL={url}")
            self.visited.add(url)

            try:
                response = self.client.get(url)
            except Exception as e:
                print(f"[Error] Failed to fetch {url}: {e}")
                continue

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                # Skip non-HTML resources
                continue

            links = self.extract_links(response.text, url)

            for link in links:
                if link not in self.visited and link not in self.discovered:
                    next_depth = depth + 1
                    if next_depth <= self.max_depth:
                        self.discovered[link] = next_depth
                        queue.append((link, next_depth))

        return list(self.visited)
