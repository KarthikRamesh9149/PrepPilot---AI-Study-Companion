from __future__ import annotations

from dataclasses import dataclass

import pytest

from exam_helper.ingestion.loaders import load_documents_from_paths, save_uploaded_files


@dataclass
class FakeUpload:
    name: str
    content: bytes = b"content"

    def getvalue(self) -> bytes:
        return self.content


def test_save_uploaded_files_sanitizes_names_and_stays_in_uploads_dir(tmp_path) -> None:
    module_dir = tmp_path / "module"
    files = [
        FakeUpload(r"..\..\secrets.pdf", b"first"),
        FakeUpload("../secrets.pdf", b"second"),
        FakeUpload("lecture:one?.pptx", b"third"),
    ]

    saved = save_uploaded_files(files, module_dir)

    uploads_dir = module_dir / "uploads"
    assert [path.name for path in saved] == ["secrets.pdf", "secrets-2.pdf", "lecture_one_.pptx"]
    assert [path.read_bytes() for path in saved] == [b"first", b"second", b"third"]
    assert all(path.parent == uploads_dir for path in saved)


def test_save_uploaded_files_rejects_unsupported_extensions(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        save_uploaded_files([FakeUpload("notes.txt")], tmp_path / "module")


def test_load_documents_rejects_legacy_ppt(tmp_path) -> None:
    ppt_file = tmp_path / "slides.ppt"
    ppt_file.write_bytes(b"not a modern pptx")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_documents_from_paths([ppt_file])
