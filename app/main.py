import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import auth, library, reader
from .config import settings
from .database import engine, Base

# Create tables if they don't exist (useful for dev, though we have schema.sql)
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="My Reader")

# Mount static files? We don't have a static folder yet, but if we did:
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(library.router)
app.include_router(reader.router)

if __name__ == "__main__":
    print("Starting server at http://127.0.0.1:8123")
    uvicorn.run(app, host="127.0.0.1", port=8123)
