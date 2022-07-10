from pathlib import Path
from typing import Iterable

import jinja2
import pdfkit  # type: ignore  # Skip type checking this module - no library stubs

from doxhell.loaders import Test


def render_protocol(tests: Iterable[Test]) -> str:
    """Render the manual test protocol."""
    html_file = _render_html(tests)
    return _render_pdf(html_file)


def _render_html(tests: Iterable[Test]) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
    template = env.get_template("test-protocol.jinja")
    with open(Path("templates") / "style.css", "r") as css_file:
        stylesheet = css_file.read()
    output = template.render(tests=tests, stylesheet=stylesheet)
    html_filename = "test-protocol.html"
    with open(html_filename, "w") as file:
        file.write(output)

    return html_filename


def _render_pdf(html_file: str) -> str:
    pdf_filename = "test-protocol.pdf"
    pdfkit.from_file(html_file, pdf_filename, options={"enable-forms": True})
    return pdf_filename
