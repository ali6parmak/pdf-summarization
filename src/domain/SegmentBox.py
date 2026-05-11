from pdf_token_type_labels import TokenType
from pydantic import BaseModel


class SegmentBox(BaseModel):
    left: float
    top: float
    width: float
    height: float
    page_number: int
    page_width: int
    page_height: int
    text: str = ""
    type: TokenType = TokenType.TEXT
    id: str = ""

    def __hash__(self):
        return hash(
            (
                self.left,
                self.top,
                self.width,
                self.height,
                self.page_number,
                self.page_width,
                self.page_height,
                self.text,
                self.type,
                self.id,
            )
        )

    def to_dict(self):
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "page_number": self.page_number,
            "page_width": self.page_width,
            "page_height": self.page_height,
            "text": self.text,
            "type": self.type.value,
        }

if __name__ == "__main__":
    a = TokenType.TEXT
    print(a.value)
