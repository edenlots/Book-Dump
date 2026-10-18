"""Backward-compatible exports for the split query modules."""

from .book_queries import BookQueries
from .log_queries import LogQueries
from .user_queries import UserQueries

__all__ = ["UserQueries", "BookQueries", "LogQueries"]
