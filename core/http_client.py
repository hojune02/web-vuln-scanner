# core/http_client.py

from urllib.parse import urljoin, urlparse

import requests


class HttpClient:
    """
    Thin wrapper around requests.Session for consistent headers, timeouts, etc.
    """

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout

        # Basic default headers – can be expanded later
        self.session.headers.update(
            {
                "User-Agent": (
                    "WebVulnScanner/0.1 (+https://github.com/your-username/web-vuln-scanner)"
                )
            }
        )

        parsed = urlparse(self.base_url)
        self.base_domain = parsed.netloc

    def get_full_url(self, url: str) -> str:
        """
        Turn relative URLs into absolute, based on base_url.
        """
        return urljoin(self.base_url, url)

    def same_domain(self, url: str) -> bool:
        """
        Check whether the URL is within the original domain.
        """
        parsed = urlparse(url)
        return parsed.netloc == "" or parsed.netloc == self.base_domain

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Perform a GET request with sensible defaults.
        """
        full_url = self.get_full_url(url)
        resp = self.session.get(full_url, timeout=self.timeout, **kwargs)
        return resp
