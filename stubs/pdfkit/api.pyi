from collections.abc import Iterable
from io import IOBase

from pdfkit.configuration import Configuration

def from_url(
    url: str | IOBase,
    output_path: str | None = ...,
    options: dict | Iterable[tuple] | None = ...,
    toc: dict | None = ...,
    cover: str | None = ...,
    configuration: Configuration | None = ...,
    cover_first: bool = ...,
    verbose: bool = ...,
) -> bool | str | bytes: ...
def from_file(
    input: str | IOBase,
    output_path: str | None = ...,
    options: dict | Iterable[tuple] | None = ...,
    toc: dict | None = ...,
    cover: str | None = ...,
    css: str | list[str] | None = ...,
    configuration: Configuration | None = ...,
    cover_first: bool = ...,
    verbose: bool = ...,
) -> bool | str | bytes: ...
def from_string(
    input: str | IOBase,
    output_path: str | None = ...,
    options: dict | Iterable[tuple] | None = ...,
    toc: dict | None = ...,
    cover: str | None = ...,
    css: str | list[str] | None = ...,
    configuration: Configuration | None = ...,
    cover_first: bool = ...,
    verbose: bool = ...,
) -> bool | str | bytes: ...
def configuration(**kwargs: str): ...
