import os
import sys
from pathlib import Path


class DataProcessor:
    """Processes data."""

    def __init__(self, config: dict) -> None:
        self.config = config

    def process(self, data: list) -> list:
        """Main processing logic."""
        return [self._transform(item) for item in data]

    def _transform(self, item):
        return item


def load_data(path: str) -> list:
    """Load data from a file."""
    with open(path) as f:
        return f.readlines()


CONSTANT = "value"
