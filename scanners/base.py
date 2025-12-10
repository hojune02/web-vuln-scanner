# scanners/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ScanResult:
    def __init__(self, url: str, vuln_name: str, severity: str, detail: str):
        self.url = url
        self.vuln_name = vuln_name
        self.severity = severity
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "vulnerability": self.vuln_name,
            "severity": self.severity,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        return f"[{self.severity}] {self.vuln_name} at {self.url} – {self.detail}"


class BaseScanner(ABC):
    """
    Interface all vulnerability scanners must implement.
    """

    name: str = "base"
    description: str = "Base scanner"

    @abstractmethod
    def scan(self, url: str) -> List[ScanResult]:
        """
        Scan a single URL and return a list of results.
        """
        raise NotImplementedError
