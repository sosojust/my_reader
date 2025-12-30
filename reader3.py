"""
Parses an EPUB file into a structured object that can be used to serve the book via a web interface.
"""

import os
import pickle
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import unquote

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, Comment
import fitz  # PyMuPDF

# --- Data structures ---

@dataclass
class ChapterContent:
    """
    Represents a physical file in the EPUB (Spine Item).
    A single file might contain multiple logical chapters (TOC entries).
    """
    id: str           # Internal ID (e.g., 'item_1')
    href: str         # Filename (e.g., 'part01.html')
    title: str        # Best guess title from file
    content: str      # Cleaned HTML with rewritten image paths
    text: str         # Plain text for search/LLM context
    order: int        # Linear reading order


@dataclass
class TOCEntry:
    """Represents a logical entry in the navigation sidebar."""
    title: str
    href: str         # original href (e.g., 'part01.html#chapter1')
    file_href: str    # just the filename (e.g., 'part01.html')
    anchor: str       # just the anchor (e.g., 'chapter1'), empty if none
    children: List['TOCEntry'] = field(default_factory=list)


@dataclass
class BookMetadata:
    """Metadata"""
    title: str
    language: str
    authors: List[str] = field(default_factory=list)
    description: Optional[str] = None
    publisher: Optional[str] = None
    date: Optional[str] = None
    identifiers: List[str] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)


@dataclass
class Book:
    """The Master Object to be pickled."""
    metadata: BookMetadata
    spine: List[ChapterContent]  # The actual content (linear files)
    toc: List[TOCEntry]          # The navigation tree
    images: Dict[str, str]       # Map: original_path -> local_path

    # Meta info
    source_file: str
    processed_at: str
    version: str = "3.0"


# --- Utilities ---

def clean_html_content(soup: BeautifulSoup) -> BeautifulSoup:

    # Remove dangerous/useless tags
    for tag in soup(['script', 'style', 'iframe', 'video', 'nav', 'form', 'button']):
        tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove input tags
    for tag in soup.find_all('input'):
        tag.decompose()

    return soup


def extract_plain_text(soup: BeautifulSoup) -> str:
    """Extract clean text for LLM/Search usage."""
    text = soup.get_text(separator=' ')
    # Collapse whitespace
    return ' '.join(text.split())


def parse_toc_recursive(toc_list, depth=0) -> List[TOCEntry]:
    """
    Recursively parses the TOC structure from ebooklib.
    """
    result = []

    for item in toc_list:
        # ebooklib TOC items are either `Link` objects or tuples (Section, [Children])
        if isinstance(item, tuple):
            section, children = item
            entry = TOCEntry(
                title=section.title,
                href=unquote(section.href),
                file_href=unquote(section.href.split('#')[0]),
                anchor=section.href.split('#')[1] if '#' in section.href else "",
                children=parse_toc_recursive(children, depth + 1)
            )
            result.append(entry)
        elif isinstance(item, epub.Link):
            entry = TOCEntry(
                title=item.title,
                href=unquote(item.href),
                file_href=unquote(item.href.split('#')[0]),
                anchor=item.href.split('#')[1] if '#' in item.href else ""
            )
            result.append(entry)
        # Note: ebooklib sometimes returns direct Section objects without children
        elif isinstance(item, epub.Section):
             entry = TOCEntry(
                title=item.title,
                href=unquote(item.href),
                file_href=unquote(item.href.split('#')[0]),
                anchor=item.href.split('#')[1] if '#' in item.href else ""
            )
             result.append(entry)

    return result


def get_fallback_toc(book_obj) -> List[TOCEntry]:
    """
    If TOC is missing, build a flat one from the Spine.
    """
    toc = []
    for item in book_obj.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            name = item.get_name()
            # Try to guess a title from the content or ID
            title = item.get_name().replace('.html', '').replace('.xhtml', '').replace('_', ' ').title()
            toc.append(TOCEntry(title=title, href=name, file_href=name, anchor=""))
    return toc


def extract_metadata_robust(book_obj) -> BookMetadata:
    """
    Extracts metadata handling both single and list values.
    """
    def get_list(key):
        data = book_obj.get_metadata('DC', key)
        return [x[0] for x in data] if data else []

    def get_one(key):
        data = book_obj.get_metadata('DC', key)
        return data[0][0] if data else None

    return BookMetadata(
        title=get_one('title') or "Untitled",
        language=get_one('language') or "en",
        authors=get_list('creator'),
        description=get_one('description'),
        publisher=get_one('publisher'),
        date=get_one('date'),
        identifiers=get_list('identifier'),
        subjects=get_list('subject')
    )


def process_pdf(pdf_path: str, output_dir: str) -> Book:
    """
    Parses a PDF file into a structured Book object.
    Each page is treated as a chapter/image.
    """
    # 1. Load PDF
    print(f"Loading {pdf_path}...")
    doc = fitz.open(pdf_path)

    # 2. Extract Metadata
    metadata = BookMetadata(
        title=doc.metadata.get('title') or os.path.basename(pdf_path),
        language="en", # Default
        authors=[doc.metadata.get('author')] if doc.metadata.get('author') else [],
        description=doc.metadata.get('subject'),
        publisher=doc.metadata.get('producer'),
        date=doc.metadata.get('creationDate'),
        identifiers=[],
        subjects=doc.metadata.get('keywords', '').split(',') if doc.metadata.get('keywords') else []
    )

    # 3. Prepare Output Directories
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    image_map = {}
    spine_chapters = []
    toc_structure = []

    # 4. Process Pages
    print("Processing pages...")
    for i, page in enumerate(doc):
        # Render page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better quality
        image_filename = f"page_{i+1}.png"
        image_path = os.path.join(images_dir, image_filename)
        pix.save(image_path)
        
        rel_path = f"images/{image_filename}"
        image_map[image_filename] = rel_path

        # Extract text for search/LLM
        text = page.get_text()

        # Create Content
        # We wrap the image in a simple HTML structure
        content_html = f'''
        <div style="text-align: center;">
            <img src="{rel_path}" style="max-width: 100%; height: auto;" />
        </div>
        '''

        chapter_id = f"page_{i+1}"
        chapter_title = f"Page {i+1}"
        
        chapter = ChapterContent(
            id=chapter_id,
            href=chapter_id,
            title=chapter_title,
            content=content_html,
            text=text,
            order=i
        )
        spine_chapters.append(chapter)
        
        # Add to TOC (flat structure for now)
        # Or maybe only add every 10 pages or utilize PDF outline if available?
        # For now, let's add every page to TOC is too much? 
        # Let's try to get PDF TOC (outline)
    
    # 5. Process TOC from PDF Outline
    print("Parsing Table of Contents...")
    pdf_toc = doc.get_toc()
    if pdf_toc:
        # pdf_toc is list of [lvl, title, page_num, dest]
        def build_toc(toc_items, current_idx=0, current_level=1):
            result = []
            while current_idx < len(toc_items):
                item = toc_items[current_idx]
                lvl = item[0]
                title = item[1]
                page_num = item[2]
                
                if lvl < current_level:
                    return result, current_idx
                
                if lvl == current_level:
                    # Create entry
                    # Page num is 1-based in get_toc
                    target_page_idx = page_num - 1
                    if 0 <= target_page_idx < len(spine_chapters):
                        # Link to the page chapter
                        entry = TOCEntry(
                            title=title,
                            href=spine_chapters[target_page_idx].href,
                            file_href=spine_chapters[target_page_idx].href,
                            anchor=""
                        )
                        current_idx += 1
                        # Check for children
                        children, next_idx = build_toc(toc_items, current_idx, current_level + 1)
                        entry.children = children
                        result.append(entry)
                        current_idx = next_idx
                    else:
                        current_idx += 1
                else:
                    # Should be handled by recursive call
                     return result, current_idx
            return result, current_idx

        toc_structure, _ = build_toc(pdf_toc)
    
    # Fallback TOC if empty
    if not toc_structure:
        # Create a simple TOC: Page 1, Page 10, Page 20...
        for i in range(0, len(spine_chapters), 10): # Every 10 pages
             chapter = spine_chapters[i]
             toc_structure.append(TOCEntry(
                 title=chapter.title,
                 href=chapter.href,
                 file_href=chapter.href,
                 anchor=""
             ))

    doc.close()

    # 6. Final Assembly
    final_book = Book(
        metadata=metadata,
        spine=spine_chapters,
        toc=toc_structure,
        images=image_map,
        source_file=os.path.basename(pdf_path),
        processed_at=datetime.now().isoformat()
    )

    return final_book


# --- Main Conversion Logic ---

def process_epub(epub_path: str, output_dir: str) -> Book:

    # 1. Load Book
    print(f"Loading {epub_path}...")
    book = epub.read_epub(epub_path)

    # 2. Extract Metadata
    metadata = extract_metadata_robust(book)

    # 3. Prepare Output Directories
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # 4. Extract Images & Build Map
    print("Extracting images...")
    image_map = {} # Key: internal_path, Value: local_relative_path

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            # Normalize filename
            original_fname = os.path.basename(item.get_name())
            # Sanitize filename for OS
            safe_fname = "".join([c for c in original_fname if c.isalpha() or c.isdigit() or c in '._-']).strip()

            # Save to disk
            local_path = os.path.join(images_dir, safe_fname)
            with open(local_path, 'wb') as f:
                f.write(item.get_content())

            # Map keys: We try both the full internal path and just the basename
            # to be robust against messy HTML src attributes
            rel_path = f"images/{safe_fname}"
            image_map[item.get_name()] = rel_path
            image_map[original_fname] = rel_path

    # 5. Process TOC
    print("Parsing Table of Contents...")
    toc_structure = parse_toc_recursive(book.toc)
    if not toc_structure:
        print("Warning: Empty TOC, building fallback from Spine...")
        toc_structure = get_fallback_toc(book)

    # 6. Process Content (Spine-based to preserve HTML validity)
    print("Processing chapters...")
    spine_chapters = []

    # We iterate over the spine (linear reading order)
    for i, spine_item in enumerate(book.spine):
        item_id, linear = spine_item
        item = book.get_item_with_id(item_id)

        if not item:
            continue

        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Raw content
            raw_content = item.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(raw_content, 'html.parser')

            # A. Fix Images
            for img in soup.find_all(['img', 'image']):
                # EPUBs can use xlink:href in <image> tags (SVG)
                src = img.get('src') or img.get('xlink:href') or img.get('href')
                if not src: continue

                # Decode URL (part01/image%201.jpg -> part01/image 1.jpg)
                src_decoded = unquote(src)
                filename = os.path.basename(src_decoded)

                # Try to find in map
                if src_decoded in image_map:
                    new_src = image_map[src_decoded]
                elif filename in image_map:
                    new_src = image_map[filename]
                else:
                    new_src = None
                
                if new_src:
                    # Update the correct attribute
                    if img.name == 'image':
                        # Be robust: some parsers strip namespaces, some keep them.
                        # We try to update all likely candidates.
                        if img.has_attr('xlink:href'):
                            img['xlink:href'] = new_src
                        if img.has_attr('href'):
                            img['href'] = new_src
                        if img.has_attr('src'):
                            img['src'] = new_src
                    else:
                        img['src'] = new_src

            # B. Clean HTML
            soup = clean_html_content(soup)

            # C. Extract Body Content only
            body = soup.find('body')
            if body:
                # Extract inner HTML of body
                final_html = "".join([str(x) for x in body.contents])
            else:
                final_html = str(soup)

            # D. Create Object
            chapter = ChapterContent(
                id=item_id,
                href=item.get_name(), # Important: This links TOC to Content
                title=f"Section {i+1}", # Fallback, real titles come from TOC
                content=final_html,
                text=extract_plain_text(soup),
                order=i
            )
            spine_chapters.append(chapter)

    # 7. Final Assembly
    final_book = Book(
        metadata=metadata,
        spine=spine_chapters,
        toc=toc_structure,
        images=image_map,
        source_file=os.path.basename(epub_path),
        processed_at=datetime.now().isoformat()
    )

    return final_book


def save_to_pickle(book: Book, output_dir: str):
    p_path = os.path.join(output_dir, 'book.pkl')
    with open(p_path, 'wb') as f:
        pickle.dump(book, f)
    print(f"Saved structured data to {p_path}")


# --- CLI ---

if __name__ == "__main__":

    import sys
    if len(sys.argv) < 2:
        print("Usage: python reader3.py <file.epub> [output_dir]")
        sys.exit(1)

    epub_file = sys.argv[1]
    assert os.path.exists(epub_file), "File not found."
    
    # Allow optional output directory argument
    if len(sys.argv) >= 3:
        out_dir = sys.argv[2]
    else:
        out_dir = os.path.splitext(epub_file)[0] + "_data"

    book_obj = process_epub(epub_file, out_dir)
    save_to_pickle(book_obj, out_dir)
    print("\n--- Summary ---")
    print(f"Title: {book_obj.metadata.title}")
    print(f"Authors: {', '.join(book_obj.metadata.authors)}")
    print(f"Physical Files (Spine): {len(book_obj.spine)}")
    print(f"TOC Root Items: {len(book_obj.toc)}")
    print(f"Images extracted: {len(book_obj.images)}")
