from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Bookshelf")


class Book(BaseModel):
    title: str
    author: str
    year: int


BOOKS: list[Book] = [
    Book(title="The Pragmatic Programmer", author="Hunt & Thomas", year=1999),
    Book(title="Clean Code", author="Robert C. Martin", year=2008),
    Book(title="Designing Data-Intensive Applications", author="Martin Kleppmann", year=2017),
    Book(title="Refactoring", author="Martin Fowler", year=1999),
    Book(title="The Mythical Man-Month", author="Fred Brooks", year=1975),
]


@app.get("/books")
def list_books(page: int = 1, size: int = 2) -> list[Book]:
    start = (page - 1) * size
    return BOOKS[start : start + size + 1]


@app.post("/books", status_code=201)
def add_book(book: Book) -> Book:
    BOOKS.append(book)
    return book
