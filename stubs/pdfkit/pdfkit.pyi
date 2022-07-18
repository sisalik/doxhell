from collections.abc import Iterable
from io import IOBase

from pdfkit.configuration import Configuration

class PDFKit:
    class ImproperSourceError(Exception):
        def __init__(self, msg: str) -> None: ...

    def __init__(
        self,
        url_or_file: str | IOBase,
        type_: str,
        options: dict | Iterable[tuple] | None = ...,
        toc: dict | None = ...,
        cover: str | None = ...,
        css: str | list[str] | None = ...,
        configuration: Configuration | None = ...,
        cover_first: bool = ...,
        verbose: bool = ...,
    ) -> None: ...
    def command(self, path: str | None = ...) -> list[str]: ...
    @staticmethod
    def handle_error(exit_code: int, stderr: str) -> None: ...
    def to_pdf(self, path: str | None = ...) -> bool | str | bytes: ...
