# web-vuln-scanner

This is an implementation of a simple web vulnerability scanner using python; this is a personal project belonging to Hojune Kim. 

## core

This section directory explains the main functionalities of the Python programs in the `core` directory, going through the main classes and functions.

### crawler.py

The python class `Crawler` is a simple BFS web crawler that stays within the same domain while keeping track of its search depth.

`__init__()` defines the elements that make up a `Crawler` object. `client` is a HttpClient, while `max_depth` and `max_pages` set the maximum search depth and no. of pages, respectively. For conducting BFS search, we keep `visited` and `discovered` sets for tracking.

`_normalize_url()` function parses the given URL nicely, using `urllib.parse.urlparse()`function and the resulting `ParseResult`'s `_replace()` function.

`extract_links()` function extracts all links from the HTML that are in the same domain. It first defines a `BeautifulSoup` object for HTML, along with am empty list `links` for storing all the extracted links. Then, the `BeautifulSoup` object looks for all the hrefs, and join the hrefs with the `current_url`. If the resultant joing url is within the same domain, we add it to `links`. The function returns `links` after completing its extraction.

`crawl()` function is the main BFS web crawl function. Starting from the given `start_url` and adding it to a deque, it performs BFS by using functions such as `deque().popleft()` and `deque().append()`.

- A pair of `(url, depth)` gets appended to the deque.
- A response from accessing the `url` is stored in `response`. Using `extract_links()` on `response.text` results in discovering new links, whose depths are now `depth + 1`. Add these new pairs of `(url, depth)` to the deque.
- Repeat the process while the deque is not empty and `len(self.visited) < self.max_pages`. If `depth + 1` is greater than `self.max_depth`, we simply do not add the corresponding `(url, depth)` pair to the deque.

### http_client.py

