from reportlab.pdfgen import canvas

from exam_helper.ingestion.loaders import load_pdf


def test_loaders_pdf_metadata(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Hello PDF page one")
    c.showPage()
    c.drawString(100, 750, "Hello PDF page two")
    c.save()

    docs = load_pdf(pdf_path)
    assert len(docs) == 2
    assert docs[0].metadata["source_file"] == "sample.pdf"
    assert docs[0].metadata["source_type"] == "pdf"
    assert docs[0].metadata["page_or_slide_number"] == 1
    assert docs[1].metadata["page_or_slide_number"] == 2
