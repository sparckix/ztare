"""Deterministic document extraction for Workbench activation.

Binary originals remain immutable attachments. The loop consumes a text projection with a receipt naming the
original hash and extraction method. Office formats use ZIP/XML structure; PDF uses ``pdftotext`` when present
and fails closed when no extractor is installed.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT_EXTENSIONS = frozenset({".md", ".txt", ".csv", ".tsv", ".json", ".log"})
BINARY_EXTENSIONS = frozenset({".pdf", ".docx", ".pptx", ".xlsx"})
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | BINARY_EXTENSIONS
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 400_000
MAX_ZIP_ENTRIES = 5_000
MAX_ZIP_UNCOMPRESSED = 64 * 1024 * 1024


class DocumentIngestError(ValueError):
    pass


def _safe_zip(data: bytes) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise DocumentIngestError("document is not a valid Office ZIP package") from exc
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_ZIP_UNCOMPRESSED:
        archive.close()
        raise DocumentIngestError("document expands beyond the extraction safety limit")
    return archive


def _xml(data: bytes) -> ET.Element:
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise DocumentIngestError("document contains malformed XML") from exc


def _paragraph_text(node: ET.Element) -> str:
    return "".join((child.text or "") for child in node.iter() if child.tag.endswith("}t")).strip()


def _docx_text(data: bytes) -> str:
    with _safe_zip(data) as archive:
        try:
            root = _xml(archive.read("word/document.xml"))
        except KeyError as exc:
            raise DocumentIngestError("DOCX has no word/document.xml") from exc
    paragraphs = [_paragraph_text(node) for node in root.iter() if node.tag.endswith("}p")]
    return "\n\n".join(text for text in paragraphs if text)


def _numbered_member(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)(?=\.xml$)", name)
    return (int(match.group(1)) if match else 10**9, name)


def _pptx_text(data: bytes) -> str:
    blocks: list[str] = []
    with _safe_zip(data) as archive:
        slides = sorted((name for name in archive.namelist()
                         if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=_numbered_member)
        for index, name in enumerate(slides, start=1):
            root = _xml(archive.read(name))
            lines = [(node.text or "").strip() for node in root.iter() if node.tag.endswith("}t")]
            body = "\n".join(line for line in lines if line)
            if body:
                blocks.append(f"## Slide {index}\n\n{body}")
    return "\n\n".join(blocks)


def _xlsx_text(data: bytes) -> str:
    with _safe_zip(data) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = _xml(archive.read("xl/sharedStrings.xml"))
            for item in (node for node in root.iter() if node.tag.endswith("}si")):
                shared.append("".join((n.text or "") for n in item.iter() if n.tag.endswith("}t")))
        sheets = sorted((name for name in archive.namelist()
                         if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)), key=_numbered_member)
        blocks: list[str] = []
        for index, name in enumerate(sheets, start=1):
            root = _xml(archive.read(name))
            rows: list[str] = []
            for row in (node for node in root.iter() if node.tag.endswith("}row")):
                values: list[str] = []
                for cell in (node for node in row if node.tag.endswith("}c")):
                    kind = cell.attrib.get("t", "")
                    raw = next(((n.text or "") for n in cell.iter() if n.tag.endswith("}v")), "")
                    if kind == "s" and raw.isdigit() and int(raw) < len(shared):
                        value = shared[int(raw)]
                    elif kind == "inlineStr":
                        value = "".join((n.text or "") for n in cell.iter() if n.tag.endswith("}t"))
                    else:
                        value = raw
                    values.append(value.replace("\t", " ").replace("\n", " "))
                if any(values):
                    rows.append("\t".join(values).rstrip())
            if rows:
                blocks.append(f"## Sheet {index}\n\n" + "\n".join(rows))
    return "\n\n".join(blocks)


def _pdf_text(data: bytes) -> str:
    executable = shutil.which("pdftotext")
    if not executable:
        raise DocumentIngestError("PDF extraction requires the pdftotext executable")
    proc = subprocess.run([executable, "-layout", "-", "-"], input=data, capture_output=True, timeout=60,
                          check=False)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise DocumentIngestError(f"PDF extraction failed: {detail[:240]}")
    return proc.stdout.decode("utf-8", errors="replace")


def _text_bytes(data: bytes, extension: str) -> str:
    text = data.decode("utf-8-sig", errors="replace")
    if extension == ".json":
        try:
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return text
    return text


def extract_document_bytes(filename: str, data: bytes) -> dict:
    name = Path(str(filename or "")).name
    extension = Path(name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentIngestError(f"unsupported document type {extension or '(none)'}")
    if not data:
        raise DocumentIngestError("document is empty")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DocumentIngestError(f"document exceeds {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB")
    extractor = {
        ".pdf": ("pdftotext-layout", _pdf_text),
        ".docx": ("docx-xml", _docx_text),
        ".pptx": ("pptx-xml", _pptx_text),
        ".xlsx": ("xlsx-xml", _xlsx_text),
    }.get(extension)
    if extractor:
        method, fn = extractor
        text = fn(data)
    else:
        method, text = "utf8-text", _text_bytes(data, extension)
    text = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
    if not text:
        raise DocumentIngestError("document contains no extractable text")
    truncated = len(text) > MAX_EXTRACTED_CHARS
    if truncated:
        text = text[:MAX_EXTRACTED_CHARS].rstrip()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem).strip("._-") or "document"
    extracted_filename = name if extension in {".md", ".txt"} else f"{stem}.extracted.md"
    return {
        "ok": True,
        "filename": name,
        "extension": extension,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "text": text,
        "chars": len(text),
        "extraction_method": method,
        "extracted_filename": extracted_filename,
        "truncated": truncated,
    }


def extract_document_path(path: Path) -> dict:
    return extract_document_bytes(path.name, path.read_bytes())


def _selfcheck() -> None:
    plain = extract_document_bytes("memo.md", b"# Decision\n\nShip it.")
    assert plain["text"].endswith("Ship it.") and plain["extracted_filename"] == "memo.md"
    try:
        extract_document_bytes("image.png", b"x")
    except DocumentIngestError:
        pass
    else:
        raise AssertionError("unsupported binary type must fail closed")
    print("document_ingest selfcheck: OK")


if __name__ == "__main__":
    _selfcheck()
