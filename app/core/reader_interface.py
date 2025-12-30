import sys
import os
from ..config import settings

# Add base dir to path so we can import reader3
sys.path.append(settings.BASE_DIR)

try:
    from reader3 import Book, BookMetadata, ChapterContent, TOCEntry, process_epub, process_pdf, save_to_pickle
except ImportError:
    # Fallback or mock for testing if reader3 is missing
    print("Warning: Could not import reader3 from base directory.")
    pass
