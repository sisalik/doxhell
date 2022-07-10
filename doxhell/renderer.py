import enum
from typing import Dict, Iterable

import jinja2
import pdfkit  # type: ignore  # Skip type checking this module - no library stubs

from doxhell.loaders import Test


class OutputFormat(str, enum.Enum):
    """The format of the rendered output file."""

    HTML = "html"
    PDF = "pdf"


def render_protocol(
    tests: Iterable[Test],
    output_map: Dict[OutputFormat, str],
) -> None:
    """Render the manual test protocol in specified formats, to specified files."""
    html_content = _render_html(tests)
    if OutputFormat.HTML in output_map:
        with open(output_map[OutputFormat.HTML], "w") as file:
            file.write(html_content)
    if OutputFormat.PDF in output_map:
        _render_pdf(html_content, output_map[OutputFormat.PDF])


def _render_html(tests: Iterable[Test]) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
    template = env.get_template("test-protocol.jinja")
    return template.render(tests=tests)


def _render_pdf(html_content: str, pdf_path: str) -> None:
    pdfkit.from_string(html_content, pdf_path, options={"enable-forms": True})
