"""Shared PRISM Studio application command path."""

from .commands import CommandDispatcher, dispatch

__all__ = ["CommandDispatcher", "dispatch"]
