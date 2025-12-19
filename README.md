# web-vuln-scanner

This is an implementation of a simple web vulnerability scanner Psing python. A personal project of Hojune Kim.

## Implementation

This section goes through the details of `web-vuln-scanner` implementation.

### core/crawler.py

The python class `Crawler` is a simple BFS web crawler that stays within the same domain while keeping track of its search depth.

`__init__()` defines the elements that make up a `Crawler` object. `client` is a HttpClient, while `max_depth` and `max_pages` set the maximum search depth and no. of pages, respectively. For conducting BFS search, we keep `visited` and `discovered` sets for tracking.

`_normalize_url()` function parses the given URL nicely, using `urllib.parse.urlparse()`function and the resulting `ParseResult`'s `_replace()` function.

`extract_links()` function extracts all links from the HTML that are in the same domain. It first defines a `BeautifulSoup` object for HTML, along with am empty list `links` for storing all the extracted links. Then, the `BeautifulSoup` object looks for all the hrefs, and join the hrefs with the `current_url`. If the resultant joing url is within the same domain, we add it to `links`. The function returns `links` after completing its extraction.

`crawl()` function is the main BFS web crawl function. Starting from the given `start_url` and adding it to a deque, it performs BFS by using functions such as `deque().popleft()` and `deque().append()`.

- A pair of `(url, depth)` gets appended to the deque.
- A response from accessing the `url` is stored in `response`. Using `extract_links()` on `response.text` results in discovering new links, whose depths are now `depth + 1`. Add these new pairs of `(url, depth)` to the deque.
- Repeat the process while the deque is not empty and `len(self.visited) < self.max_pages`. If `depth + 1` is greater than `self.max_depth`, we simply do not add the corresponding `(url, depth)` pair to the deque.

### core/http_client.py

This program contains a wrapper class `HttpClient`, which introduces abstractions and simplifies the use of `requests.Session` object. This is needed for getting a response from the target website, checking same-domain condition, and keeping a consistent session header.

`__init__()` defines `base_url`, which is the target url. `session` attribute contains a `requests.Session()` object, which we will use to retrieve responses from the website.  `timeout` attribute is set so that requests do not run forever. `session`'s header always contains a key-value pair for *User-Agent* for keeping a constant header format. `base_domain` contains the target domain extracted from `base_url`. 

`get_full_url()` takes an `url` input and concatenate it to the `base_url` using `urljoin()`. This turns a relative url (e.g. `/login`) into an absolute one (`target.com/login`).

`same_domain()` function checks whether the given `url` and `base_domain` are the same. If the given `url` is relative, its domain is deemed to be always the same as `base_domain`. 

`get()` performs a GET request to the relative url given as input. It returns the response of the request.

### core/js_renderer.py

This program defines `JSRenderer` class, which is used in `core/dynamic_crawler.py`. The class encapsulates a `Playwright` instance for running a browser environment. The environment then runs all the Javascript elements from the target web application, and reveals the final DOM structure. 

`self.render()` function allows for accessing the HTML and final_url of the web application after running all of its JS elements. This HTML output will then be used to extract URLs.

### core/dynamic_crawler.py

The simple crawler has limitations in that it cannot view the final DOM structure of a web application after running its Javascript element. Many web applications that are Javascript-heavy (such as SPA) tend to maintain minimal HTML structures, on which the crawler cannot be utilised in the most effective manner.

The dynamic crawler addresses this issue by running all the Javascript element in a headless browser environment. This is provided by `Playwright` module in Python. The crawler now has access to finalised DOM structure, extracting SPA style routes like `#/...`. 

### scanners/base.py


