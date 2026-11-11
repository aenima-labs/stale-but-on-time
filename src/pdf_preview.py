"""Render PDF pages to PNG for visual proofing: pdf_preview.py file.pdf [pages...]"""
import sys
from pathlib import Path

import pypdfium2 as pdfium

pdf = pdfium.PdfDocument(sys.argv[1])
pages = [int(p) for p in sys.argv[2:]] or range(1, len(pdf) + 1)
out = Path(sys.argv[1]).with_suffix("")
for number in pages:
    image = pdf[number - 1].render(scale=1.6).to_pil()
    image.save(f"{out}-p{number}.png")
print(len(pdf), "pages")
