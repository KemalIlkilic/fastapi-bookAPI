from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from typing import Optional, List
from src.books.book_data import books
from src.books.schemas import Book, BookUpdateModel

book_router = APIRouter()

@book_router.get("/", response_model=List[Book])
async def get_all_books():
    return [Book(**book) for book in books]


@book_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_a_book(book_data : Book) -> dict :
    new_book = book_data.model_dump()
    books.append(new_book)
    return new_book


@book_router.get("/{book_id}")
async def get_book(book_id : int) -> dict:
    for book in books:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


@book_router.patch("/{book_id}")
async def update_book(book_id : int, book_update_data : BookUpdateModel) -> dict:
    for book in books:
        if book["id"] == book_id:
            #This ensures that only fields which were provided (i.e., not None) are included in the dictionary
            update_book = book_update_data.model_dump(exclude_unset=True)
            book.update(update_book)
            return book
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


@book_router.delete("/{book_id}")
async def delete_book(book_id : int) -> dict:
    for book in books:
        if book.get("id") == book_id:
            books.remove(book)
            return {}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")