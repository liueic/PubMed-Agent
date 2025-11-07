"""Internal PubMed MCP backend.

This package re-implements the functionality of the standalone Nodejs
pubmed-data-server so that the Python agent can call PubMed, manage caches,
and perform full-text related tasks without spawning an external MCP server.
"""

from .client import PubMedMCPClient

__all__ = ["PubMedMCPClient"]

