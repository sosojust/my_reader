import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..auth import get_current_user_required
from ..config import settings
from ..core.utils import load_book_cached

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_book_permission(db: Session, user: models.User, folder_name: str):
    """
    Verifies that the book belongs to the user.
    """
    book_record = db.query(models.Book).filter(
        models.Book.folder_name == folder_name,
        models.Book.user_id == user.id
    ).first()
    
    if not book_record:
        raise HTTPException(status_code=403, detail="You do not have permission to view this book.")
    return book_record

@router.get("/read/{book_id}", response_class=HTMLResponse)
async def redirect_to_first_chapter(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """Helper to just go to chapter 0."""
    # Check permission first
    check_book_permission(db, current_user, book_id)
    return RedirectResponse(url=f"/read/{book_id}/0")

@router.get("/read/{book_id}/{chapter_index}", response_class=HTMLResponse)
async def read_chapter(
    request: Request, 
    book_id: str, 
    chapter_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """The main reader interface."""
    # Check permission
    check_book_permission(db, current_user, book_id)

    book = load_book_cached(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book data not found")

    if chapter_index < 0 or chapter_index >= len(book.spine):
        raise HTTPException(status_code=404, detail="Chapter not found")

    current_chapter = book.spine[chapter_index]

    # Calculate Prev/Next links
    prev_idx = chapter_index - 1 if chapter_index > 0 else None
    next_idx = chapter_index + 1 if chapter_index < len(book.spine) - 1 else None

    return templates.TemplateResponse("reader.html", {
        "request": request,
        "book": book,
        "current_chapter": current_chapter,
        "chapter_index": chapter_index,
        "book_id": book_id,
        "prev_idx": prev_idx,
        "next_idx": next_idx,
        "user": current_user
    })

@router.get("/read/{book_id}/images/{image_name}")
async def serve_image(
    book_id: str, 
    image_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """
    Serves images specifically for a book.
    """
    # Check permission
    check_book_permission(db, current_user, book_id)

    # Security check: ensure book_id is clean
    safe_book_id = os.path.basename(book_id)
    safe_image_name = os.path.basename(image_name)

    img_path = os.path.join(settings.DATA_DIR, safe_book_id, "images", safe_image_name)

    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(img_path)
