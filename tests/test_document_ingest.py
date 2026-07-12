from __future__ import annotations

import io
import zipfile

import pytest

from ztare.workspace.document_ingest import DocumentIngestError, extract_document_bytes


def _office_zip(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, text in files.items():
            archive.writestr(path, text)
    return out.getvalue()


def test_extracts_docx_paragraphs_with_a_stable_receipt():
    raw = _office_zip({
        "word/document.xml": (
            '<w:document xmlns:w="urn:w"><w:body>'
            '<w:p><w:r><w:t>Decision memo</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Launch only if churn stays below 3%.</w:t></w:r></w:p>'
            '</w:body></w:document>'
        )
    })
    result = extract_document_bytes("memo.docx", raw)
    assert result["text"] == "Decision memo\n\nLaunch only if churn stays below 3%."
    assert result["extracted_filename"] == "memo.extracted.md"
    assert result["extraction_method"] == "docx-xml"
    assert len(result["sha256"]) == 64


def test_extracts_pptx_in_slide_order():
    raw = _office_zip({
        "ppt/slides/slide2.xml": '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>Second</a:t></p:sld>',
        "ppt/slides/slide1.xml": '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>First</a:t></p:sld>',
    })
    result = extract_document_bytes("review.pptx", raw)
    assert result["text"].index("First") < result["text"].index("Second")
    assert "## Slide 1" in result["text"] and "## Slide 2" in result["text"]


def test_extracts_xlsx_shared_and_numeric_cells():
    raw = _office_zip({
        "xl/sharedStrings.xml": '<sst xmlns="urn:x"><si><t>Metric</t></si><si><t>Revenue</t></si></sst>',
        "xl/worksheets/sheet1.xml": (
            '<worksheet xmlns="urn:x"><sheetData><row>'
            '<c t="s"><v>0</v></c><c t="s"><v>1</v></c><c><v>42</v></c>'
            '</row></sheetData></worksheet>'
        ),
    })
    result = extract_document_bytes("model.xlsx", raw)
    assert "Metric\tRevenue\t42" in result["text"]


def test_rejects_unknown_binary_types():
    with pytest.raises(DocumentIngestError, match="unsupported document type"):
        extract_document_bytes("scan.png", b"not a supported document")
