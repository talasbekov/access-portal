"""Utility package exposing core modules for testing."""
import importlib

try:
    main = importlib.import_module('main')
except Exception:
    main = None  # pragma: no cover

__all__ = ['main']
