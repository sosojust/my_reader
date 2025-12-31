import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..auth import get_current_user_required, get_current_user
from ..config import settings
from ..core.reader_interface import process_epub, process_pdf, save_to_pickle
from ..core.utils import load_book_cached

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def library_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lists all available processed books for the logged-in user."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Get books from DB belonging to this user
    user_books = db.query(models.Book).filter(models.Book.user_id == current_user.id).all()
    
    books_data = []
    for db_book in user_books:
        # Load metadata from pickle
        # Note: We rely on the folder_name stored in DB
        book_obj = load_book_cached(db_book.folder_name)
        if book_obj:
            books_data.append({
                "id": db_book.folder_name, # The folder name is the ID used in URLs
                "title": db_book.title, # Use title from DB or Pickle? DB is faster for list
                "author": ", ".join(book_obj.metadata.authors),
                "chapters": len(book_obj.spine)
            })
        else:
            # Book data missing on disk?
            pass

    return templates.TemplateResponse("library.html", {
        "request": request, 
        "books": books_data,
        "user": current_user
    })

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """Handle EPUB and PDF file upload and processing."""
    filename = file.filename.lower()
    if not (filename.endswith(".epub") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Only .epub and .pdf files are supported")
    
    # Ensure directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.DATA_DIR, exist_ok=True)

    # Generate unique ID for storage
    unique_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{unique_id}{file_ext}"

    # Save uploaded file temporarily
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Process the File
        # Output directory is now in DATA_DIR
        folder_name = unique_id
        out_dir = os.path.join(settings.DATA_DIR, folder_name)
        
        if filename.endswith(".epub"):
            book_obj = process_epub(file_path, out_dir)
        else: # PDF
            book_obj = process_pdf(file_path, out_dir)

        save_to_pickle(book_obj, out_dir)
        
        # Save to DB
        # Determine the title
        # Default to original filename (without extension)
        display_title = os.path.splitext(file.filename)[0]

        # If metadata has a valid title, and it's not the auto-generated UUID filename, use it.
        # process_pdf falls back to os.path.basename(file_path) which is the UUID filename.
        saved_basename = os.path.basename(file_path) # e.g. uuid.pdf

        if book_obj.metadata.title:
            meta_title = book_obj.metadata.title.strip()
            if meta_title and meta_title != saved_basename and meta_title != "Untitled":
                display_title = meta_title

        new_book = models.Book(
            title=display_title,
            author=", ".join(book_obj.metadata.authors) if book_obj.metadata.authors else None,
            publisher=book_obj.metadata.publisher,
            published_date=book_obj.metadata.date,
            description=book_obj.metadata.description,
            language=book_obj.metadata.language,
            sections_count=len(book_obj.spine),
            folder_name=folder_name,
            user_id=current_user.id
        )
        db.add(new_book)
        db.commit()
        
    except Exception as e:
        print(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
        
    return RedirectResponse(url="/", status_code=303)
