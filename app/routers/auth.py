from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import verify_password, get_password_hash, create_access_token, get_current_user
from datetime import timedelta
from ..config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    db: Session = Depends(get_db)
):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    
    if not email or not password:
         return templates.TemplateResponse("register.html", {"request": request, "error": "Email and password are required"})

    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})

    new_user = models.User(
        email=email,
        password_hash=get_password_hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Auto login after register? Or redirect to login? Let's redirect to login.
    return RedirectResponse(url="/login?registered=true", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    success_msg = None
    if request.query_params.get("registered"):
        success_msg = "Registration successful! Please login."
    return templates.TemplateResponse("login.html", {"request": request, "success": success_msg})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Set Cookie
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return resp

@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp
