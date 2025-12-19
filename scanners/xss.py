# Obsolete Static XSS Scanner
from .base import ScanResult, BaseScanner
from core.http_client import HttpClient

from typing import List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

class XSSScanner(BaseScanner):
    def __init__(self, client: HttpClient):
        self.client = client
        self.payloads = [
            "<script>alert(1337)</script>",
            "\"'><svg onload=alert(1337)>",
        ]

    def _change_url_with_payload(self, url: str, param_name: str, payload: str) -> str:
        parsed = urlparse(url)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)

        new_params = []
        for key, value in query_params:
            if key == param_name:
                new_params.append((key, payload))
            else:
                new_params.append((key, value))

        new_query = urlencode(new_params, doseq=True)
        changed_url_parsed = parsed._replace(query=new_query)

        return urlunparse(changed_url_parsed)
    
    def _extract_param_names(self, url: str) -> list[str]:
        parsed = urlparse(url)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)

        params = sorted(set(key for key, _ in query_params))
        return params
    
    def scan(self, url: str) -> list[ScanResult]:

        results: list[ScanResult] = []

        param_names = self._extract_param_names(url)

        if not param_names:
            return results

        print(f"[XSS] Testing URL with params: {url}")

        for param in param_names:
            for payload in self.payloads:
                test_url = self._change_url_with_payload(url, param, payload)

                try:
                    resp = self.client.get(test_url)
                except Exception as e:
                    print(f"[XSS] Error requesting {test_url}: {e}")
                    continue

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    continue

                body = resp.text

                if payload in body:
                    detail = (
                        f"Parameter '{param}' appears to be reflected without encoding. "
                        f"Tested payload: {payload}"
                    )
                    result = ScanResult(
                        url=test_url,
                        vuln_name="Reflected XSS (basic)",
                        severity="HIGH",
                        detail=detail,
                    )
                    print(f"[XSS] Potential XSS found: {result}")
                    results.append(result)
                    break

        return results 

        