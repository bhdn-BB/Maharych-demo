"""Temporary, local document access through LangChain loaders."""
from pathlib import Path
from tempfile import TemporaryDirectory


class ResumeDocumentRepository:
    def read(self, data: bytes, kind: str):
        if kind == "pdf":
            from langchain_community.document_loaders import PyPDFLoader
            loader_class = PyPDFLoader
        else:
            from langchain_community.document_loaders import Docx2txtLoader
            loader_class = Docx2txtLoader
        with TemporaryDirectory() as directory:
            path = Path(directory) / ("resume." + kind)
            path.write_bytes(data)
            yield from (doc.page_content for doc in loader_class(str(path)).lazy_load())
