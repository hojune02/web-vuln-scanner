# scanners/dynamic_xss.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from core.js_renderer import JSRenderer
from scanners.base import BaseScanner, ScanResult


@dataclass
class FormTarget:
    url: str
    selector: str  # selector of the input/textarea we injected into
    note: str      # small description


class DynamicXSSScanner(BaseScanner):
    """
    XSS scanner for modern JS-heavy sites:
      A) Uses Playwright-rendered DOM to detect reflection.
      B) Adds coverage for SPA hash routes (e.g., /#/search?q=...).
      C) Performs form-based injection by typing payloads and attempting safe submits.
    """

    name = "dynamic_xss"
    description = "Dynamic XSS scanner using Playwright (DOM + SPA routes + forms)"

    def __init__(self, renderer: JSRenderer, wait_until: str = "networkidle"):
        self.renderer = renderer
        self.wait_until = wait_until

        # Keep payloads short & diagnostic; expand later.
        self.payloads = [
            "XSS_TEST_1337<svg onload=alert(1337)>",
            "\"><svg onload=alert(1337)>",
        ]

    # -------------------------
    # Helpers: URL mutation
    # -------------------------

    def _mutate_query_param(self, url: str, param: str, payload: str) -> str:
        """Mutate a normal URL query param: /path?param=..."""
        parsed = urlparse(url)
        params = parse_qsl(parsed.query, keep_blank_values=True)

        if not params:
            return url  # nothing to mutate

        new_params = [(k, payload if k == param else v) for (k, v) in params]
        new_query = urlencode(new_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def _extract_query_params(self, url: str) -> List[str]:
        parsed = urlparse(url)
        return sorted({k for (k, _) in parse_qsl(parsed.query, keep_blank_values=True)})

    def _add_spa_search_param_guess(self, url: str, payload: str) -> Optional[str]:
        """
        B) SPA route parameter coverage:
        If URL contains '#/search' (or ends with '/#/search'), try appending '?q=payload' inside the fragment.
        Examples:
          http://host:3000/#/search      -> http://host:3000/#/search?q=PAYLOAD
          http://host:3000/#/search?x=1  -> http://host:3000/#/search?x=1&q=PAYLOAD (simple append)
        """
        if "#/search" not in url:
            return None

        # Split only once at '#'
        base, frag = url.split("#", 1)  # base="http://host:3000/", frag="/search..."
        if "?" in frag:
            return f"{base}#{frag}&q={payload}"
        else:
            return f"{base}#{frag}?q={payload}"

    # -------------------------
    # Helpers: reflection checks
    # -------------------------

    def _looks_reflected(self, rendered_html: str, visible_text: str, payload: str) -> Tuple[bool, str]:
        """
        Checks both rendered HTML and visible text.
        Also checks a basic HTML-escaped version of '<' and '>' to catch encoded reflections.
        """
        escaped = (
            payload.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#x27;")
        )

        if payload in rendered_html:
            return True, "payload found in rendered DOM HTML"
        if payload in visible_text:
            return True, "payload found in visible text"
        if escaped in rendered_html:
            return True, "HTML-escaped payload found in rendered DOM HTML"
        if escaped in visible_text:
            return True, "HTML-escaped payload found in visible text"
        return False, ""

    # -------------------------
    # A) Dynamic “URL-based” checks
    # -------------------------

    def _render_and_check(self, test_url: str, payload: str) -> Optional[str]:
        """
        Navigate using Playwright and check reflections in rendered DOM.
        Returns a short reason string if reflected, else None.
        """
        page = self.renderer.context.new_page()
        try:
            page.goto(test_url, wait_until=self.wait_until)
            # Extra small wait helps SPAs settle after route changes
            page.wait_for_timeout(250)

            rendered_html = page.content()
            try:
                visible_text = page.inner_text("body")
            except Exception:
                visible_text = ""

            ok, why = self._looks_reflected(rendered_html, visible_text, payload)
            return why if ok else None
        finally:
            page.close()

    # -------------------------
    # C) Form-based checks
    # -------------------------

    def _find_injectable_fields(self, url: str) -> List[FormTarget]:
        """
        Find text-like inputs/areas that are likely safe to test.
        We intentionally skip password fields to avoid interacting with auth flows.
        """
        page = self.renderer.context.new_page()
        targets: List[FormTarget] = []
        try:
            page.goto(url, wait_until=self.wait_until)
            page.wait_for_timeout(250)

            # Selectors for typical text entry fields.
            selectors = [
                "input[type='text']",
                "input[type='search']",
                "input:not([type])",          # input with no type specified
                "textarea",
            ]

            # Collect a small number of targets to avoid heavy interaction
            for sel in selectors:
                handles = page.query_selector_all(sel)
                for h in handles:
                    # Skip invisible/disabled fields
                    try:
                        if not h.is_visible():
                            continue
                        if h.is_disabled():
                            continue
                    except Exception:
                        continue

                    # Skip password and hidden fields explicitly
                    t = (h.get_attribute("type") or "").lower()
                    if t in ("password", "hidden", "checkbox", "radio", "file"):
                        continue

                    # Build a stable locator selector if possible
                    # Prefer id, then name, else fallback to the original selector.
                    field_id = h.get_attribute("id")
                    field_name = h.get_attribute("name")
                    if field_id:
                        targets.append(FormTarget(url=url, selector=f"#{field_id}", note="field by id"))
                    elif field_name:
                        targets.append(FormTarget(url=url, selector=f"[name='{field_name}']", note="field by name"))
                    else:
                        targets.append(FormTarget(url=url, selector=sel, note="field by generic selector"))

                    if len(targets) >= 5:  # keep it light
                        return targets

            return targets
        finally:
            page.close()

    def _inject_into_field_and_submit(self, target: FormTarget, payload: str) -> Optional[str]:
        """
        Type payload into a field and attempt a safe submit:
        - press Enter
        - click a visible submit button (if present)
        Then check DOM for reflection.
        """
        page = self.renderer.context.new_page()
        try:
            page.goto(target.url, wait_until=self.wait_until)
            page.wait_for_timeout(250)

            locator = page.locator(target.selector).first
            # If selector is generic, ensure we pick a visible field
            try:
                locator.wait_for(state="visible", timeout=2000)
            except Exception:
                return None

            # Fill payload
            try:
                locator.fill(payload)
            except Exception:
                return None

            # Try "Enter" (often triggers search in SPAs)
            try:
                locator.press("Enter")
                page.wait_for_timeout(300)
            except Exception:
                pass

            # Try clicking a submit button if available
            # (Avoid clicking dangerous buttons like delete/checkout; keep it conservative)
            for btn_sel in ["button[type='submit']", "input[type='submit']"]:
                btns = page.query_selector_all(btn_sel)
                for b in btns:
                    try:
                        if b.is_visible() and not b.is_disabled():
                            b.click()
                            page.wait_for_timeout(400)
                            break
                    except Exception:
                        continue

            rendered_html = page.content()
            try:
                visible_text = page.inner_text("body")
            except Exception:
                visible_text = ""

            ok, why = self._looks_reflected(rendered_html, visible_text, payload)
            return why if ok else None
        finally:
            page.close()

    # -------------------------
    # Public API
    # -------------------------

    def scan(self, url: str) -> List[ScanResult]:
        results: List[ScanResult] = []

        # ---- A) Query parameter testing (dynamic DOM-based reflection) ----
        params = self._extract_query_params(url)
        for p in params:
            for payload in self.payloads:
                test_url = self._mutate_query_param(url, p, payload)
                why = self._render_and_check(test_url, payload)
                if why:
                    results.append(
                        ScanResult(
                            url=test_url,
                            vuln_name="Potential XSS (DOM/Rendered Reflection)",
                            severity="HIGH",
                            detail=f"Query param '{p}' reflected: {why}",
                        )
                    )
                    break  # one hit per param is enough

        # ---- B) SPA hash-route guessing (e.g., #/search?q=...) ----
        for payload in self.payloads:
            guessed = self._add_spa_search_param_guess(url, payload)
            if guessed:
                why = self._render_and_check(guessed, payload)
                if why:
                    results.append(
                        ScanResult(
                            url=guessed,
                            vuln_name="Potential XSS (SPA Route Param Reflection)",
                            severity="HIGH",
                            detail=f"Guessed SPA param 'q' reflected on #/search: {why}",
                        )
                    )
                    break

        # ---- C) Form-based scanning ----
        # Keep it modest: only run form scan on a few pages (avoid huge interaction explosion).
        targets = self._find_injectable_fields(url)
        for t in targets:
            for payload in self.payloads:
                why = self._inject_into_field_and_submit(t, payload)
                if why:
                    results.append(
                        ScanResult(
                            url=t.url,
                            vuln_name="Potential XSS (Form/Input Reflection)",
                            severity="HIGH",
                            detail=f"Injected into {t.selector} ({t.note}) and saw reflection: {why}",
                        )
                    )
                    break

        return results
