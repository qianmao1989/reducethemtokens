from dataclasses import dataclass, field
from typing import Optional
import functools


def my_decorator(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


@dataclass
class Point:
    x: float
    y: float

    @property
    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    @staticmethod
    def origin() -> "Point":
        return Point(0.0, 0.0)

    @classmethod
    def from_tuple(cls, t: tuple) -> "Point":
        return cls(t[0], t[1])

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point

    @property
    def width(self) -> float:
        return abs(self.bottom_right.x - self.top_left.x)

    @property
    def height(self) -> float:
        return abs(self.bottom_right.y - self.top_left.y)

    @property
    def area(self) -> float:
        return self.width * self.height


@my_decorator
def compute(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


class BaseProcessor:
    def process(self, data: list) -> list:
        raise NotImplementedError

    def validate(self, item) -> bool:
        return item is not None


class ConcreteProcessor(BaseProcessor):
    def process(self, data: list) -> list:
        return [x for x in data if self.validate(x)]
