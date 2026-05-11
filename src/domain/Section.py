from dataclasses import dataclass


@dataclass
class Section:
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
