# main.py

import argparse

from core.http_client import HttpClient
from core.crawler import Crawler

from core.dynamic_crawler import DynamicCrawler  # <-- new
from core.js_renderer import JSRenderer         # <-- new

# from scanners.xss import XSSScanner <-- Obsolete, since it is static
from scanners.dynamic_xss import DynamicXSSScanner # <-- Handling form-based XSS, query-based XSS in #/... URLs



def parse_args():
    parser = argparse.ArgumentParser(
        description="Simple Web Vulnerability Scanner (Phase 1: Crawler)"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Target base URL to crawl (e.g. https://example.com)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum crawl depth (default: 2)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of pages to crawl (default: 50)",
    )
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Use headless browser (Playwright) to render JS-heavy sites",
    )
    return parser.parse_args()

def run_crawl(client: HttpClient, args) -> list[str]:
    print("[*] Using DynamicCrawler (JS rendering enabled)")
    with JSRenderer(headless=True) as renderer:
        crawler = DynamicCrawler(
            client,
            renderer,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
        )
        visited_urls = crawler.crawl(args.url)

    return visited_urls

def main():
    args = parse_args()
    client = HttpClient(args.url)
    results = []

    print(f"[*] Starting crawl from {args.url}")

    print("[*] Using DynamicCrawler (JS rendering enabled)")
    with JSRenderer(headless=True) as renderer:
        crawler = DynamicCrawler(
            client,
            renderer,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
        )
        visited_urls = crawler.crawl(args.url)

    print("\n[*] Crawl finished. Visited URLs:")
    for url in visited_urls:
        print(f"  - {url}")

    ## XSSScanner Section Begins ##
    xss_scanner = DynamicXSSScanner(renderer)

    for url in visited_urls:
        scan_results = xss_scanner.scan(url)
        results.extend(scan_results)

    print("\n[*] XSS scan finished.")
    if not results:
        print("[-] No potential reflected XSS found (with basic checks).")
    else:
        print(f"[+] Found {len(results)} potential XSS issue(s):")
        for r in results:
            print(f"  - {r}")
    
    ## XSSScanner Section Ends ##


if __name__ == "__main__":
    main()
