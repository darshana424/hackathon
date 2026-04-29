import re
from bs4 import BeautifulSoup
from src.utils.logger import logger

def clean_html(html: str, minimal: bool = False) -> str:
    """
    Strips boilerplate and returns human-readable text.
    If minimal=True, preserves nav, footer, and header (useful for business analysis).
    """
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Remove noise tags
    noise_tags = ["script", "style", "noscript", "svg", "form", "iframe"]
    if not minimal:
        noise_tags.extend(["nav", "footer", "header", "aside", "button"])
        
    for tag in soup(noise_tags):
        tag.decompose()
        
    # 2. Extract text with spacing
    text = soup.get_text(separator="\n", strip=True)
    
    # 3. Clean whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    
    # 4. Final regex cleanup
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> list[str]:
    """
    Splits text into chunks of roughly chunk_size characters.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start += (chunk_size - overlap)
        
    return chunks
