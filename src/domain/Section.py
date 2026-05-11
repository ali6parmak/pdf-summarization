from dataclasses import dataclass


@dataclass
class Section:
    """A chunk of the document grouped under a heading.

    `level` is 1 for Titles, 2 for Section headers, and 0 for the leading
    body that appears before any heading is encountered.
    """

    heading: str
    body: str
    level: int = 2

    def render(self) -> str:
        if self.heading and self.body:
            return f"{self.heading}\n\n{self.body}"
        return self.heading or self.body

    @property
    def is_useful(self) -> bool:
        return bool(self.heading or self.body)
