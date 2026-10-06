from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_first_book_is_first():
    assert client.get("/books").json()[0]["title"] == "The Pragmatic Programmer"


def test_add_book():
    book = {"title": "Accelerate", "author": "Forsgren et al.", "year": 2018}
    assert client.post("/books", json=book).status_code == 201
