from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Album:
    name: str
    files: List[str]
    @classmethod
    def build(cls, data: Dict[str, str]) -> str:
        return ""


@dataclass
class Gallery:
    filename: str
    display_name: str
    albums: List[Album]

    @classmethod
    def build(cls, data: Dict[str, str]) -> None:
        """
        Builds and returns a Gallery instance from a dictionary.
        """
        pass

# TODO: galleries list is loaded here
galleries: List[Gallery] = []


if __name__ == "__main__":
    build(galleries)
