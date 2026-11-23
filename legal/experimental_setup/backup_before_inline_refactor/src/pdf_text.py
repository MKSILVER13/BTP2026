from pathlib import Path
import json

def extract_pdf(path, output_dir=None, ocr=False, min_chars=20):
    """Extract page-preserving text; optionally OCR sparse pages."""
    import fitz
    path = Path(path); doc = fitz.open(path); pages = []
    for number, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        if ocr and len(text) < min_chars:
            try:
                import pytesseract
                from PIL import Image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(image).strip()
            except Exception as exc:
                text += "\n[OCR unavailable: %s]" % exc
        pages.append({"page": number, "text": text, "characters": len(text)})
    result = {"source": str(path), "pages": pages, "text": "\n\n".join(p["text"] for p in pages)}
    if output_dir:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / (path.stem + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

def extract_directory(input_dir, output_dir, ocr=False):
    return [extract_pdf(p, output_dir, ocr) for p in sorted(Path(input_dir).rglob("*.pdf"))]
