"""Passive live Immunefi page acquisition for CYDRA.

This fetcher is deliberately limited to public Immunefi pages. It only acquires
program material; it never tests the target application and never grants scope.
"""
from __future__ import annotations
from urllib.request import Request, urlopen
from .program_intake import AcquiredResource, ImmunefiAcquisitionAdapter

class PublicHttpFetcher:
    def __init__(self, user_agent="CYDRA/2.0 passive program intake"):
        self.user_agent=user_agent
    def fetch(self, locator:str)->AcquiredResource:
        request=Request(locator,headers={"User-Agent":self.user_agent,"Accept":"text/html,application/xhtml+xml"},method="GET")
        with urlopen(request,timeout=30) as response:
            raw=response.read()
            content=raw.decode("utf-8",errors="replace")
            final=response.geturl()
        if final.rstrip('/') != locator.rstrip('/'):
            raise ValueError(f"unexpected redirect during passive acquisition: {locator} -> {final}")
        return AcquiredResource(locator,content,"immunefi-public-http")

def acquire_live_program(locator:str):
    """Acquire the current bounded Immunefi program page set."""
    return ImmunefiAcquisitionAdapter(PublicHttpFetcher()).acquire_contract(locator)
