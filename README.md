# web-vuln-scanner

## Quick Summary

**Built a modern web vulberability scanner that conducts JavaScript-aware crawling & dynamic XSS detection using a Playwright headless browser, and analyses single-page applications (SPAs) via rendered DOM inspection, depth-specified route discovery, and form-based input testing**

## Table of Contents

[1. Project Overview](#1-project-overview)

[2. Architecture Overview](#2-architecture-overview)

[3. Key Features](#3-key-features)

[4. How to Run Locally](#4-how-to-run-locally)

[5. Future Improvements](#5-future-improvements)

## 1. Project Overview

`web-vuln-scanner` is a web security scanner based on Python that is designed to identify potential XSS vulnerabilities in modern JavaScript-based web applications. This includes Single Page Applications (SPAs).

This project utilises a headless browser (Playwright) to execute any client-side JavaScript code, identify routes from the DOM structure, and perform vulnerability scan on the actual runtime web application.

This project focuses on identifying potential Cross-Site Scripting (XSS) vulnerabilities by performing dynamic reflection checks. This is donw by observing rendered DOM content, guessing SPA route parameters, and conducting form-based injection.

## 2. Architecture Overview

```
User / CLI
  ↓
main.py
  ├── Argument Parsing
  ├── Dynamic vs Static Mode Selection
  ├── Shared Browser Lifecycle Management
  ↓
JSRenderer (Playwright Wrapper)
  ├── Browser Launch (Chromium)
  ├── Persistent Browser Context
  ├── Page Rendering (JS execution)
  ↓
DynamicCrawler
  ├── BFS Crawl Strategy
  ├── SPA Route Discovery (#/routes)
  ├── Rendered DOM Link Extraction
  ├── Domain-Constrained Traversal
  ↓
DynamicXSSScanner
  ├── Rendered DOM Inspection
  ├── Visible Text Reflection Checks
  ├── SPA Route Parameter Guessing
  ├── Form/Input Injection
  ├── Safe Submit Heuristics
  ↓
Scan Results
  ├── URL
  ├── Vulnerability Type
  ├── Severity
  ├── Reflection Evidence

```
## 3. Key Features

- Executes client-side JS code using Playwright, accessing the actual runtime DOM structure
- Discovers SPA routes such as `#/search`, `#register`
- Preserves hash-based routing
- Detects reflection in rendered DOM HTML and visible texts
- Automatically tests routes such as:
```
http://host/#/search?q=<payload>
```
- Identifies inputs exposed for injections (`input`, `textarea`) and attempts using payloads with safe submissions via `Enter` key or buttons

## 4. How to Run Locally

First, activate Python venv and install dependencies using the following commands:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then, run against a dynamic target. [OWASP Juice Shop](https://github.com/juice-shop/juice-shop) is a great resource for this task. After installing Docker:
```bash
docker pull bkimminich/juice-shop
docker run --rm -p 3000:3000 bkimminich/juice-shop
```
Run the scanner:
```bash
python main.py \
  --url http://localhost:3000 \
  --max-depth 2 \
  --max-pages 30 \
  --dynamic
```

You will see discovered SPA routes, testing logs for dynamic XSS, and vulnerability summary if there is any finding.

## 5. Future Improvements
- More extensive SPA route coverage beyond `#/...`
- JSON report output for cleaner logging & auditing
- Modules for detecting additional vulnerabilities such as CSRF, SQL injection, ...
