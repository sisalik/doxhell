import enum
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import jinja2
import pdfkit
from loguru import logger

import doxhell.utils
from doxhell.loaders import Test


class OutputFormat(str, enum.Enum):
    """The format of the rendered output file."""

    HTML = "html"
    PDF = "pdf"


def render_protocol(
    tests: Iterable[Test],
    output_map: dict[OutputFormat, str],
    context: dict[str, Any],
) -> None:
    """Render the manual test protocol in specified formats, to specified files."""
    # Inject tests list and the logo image path into the context
    # TODO: Get paths from a config file
    context.update(
        {
            "tests": tests,
            "logo_path": str(
                doxhell.utils.get_package_path() / "templates" / "logo.png"
            ),
        }
    )
    # Initialise the Jinja2 environment
    templates_path = str(doxhell.utils.get_package_path() / "templates")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_path))
    # Render the output files
    html_content = _render_html(env, "protocol.jinja2", context)
    if OutputFormat.HTML in output_map:
        logger.info("Rendering HTML output")
        with open(output_map[OutputFormat.HTML], "w") as file:
            file.write(html_content)
    if OutputFormat.PDF in output_map:
        logger.info("Rendering PDF output")
        _render_pdf(html_content, output_map[OutputFormat.PDF], env, context)


def _render_html(
    env: jinja2.Environment, template_name: str, context: dict[str, Any]
) -> str:
    template = env.get_template(template_name)
    return template.render(**context)


def _render_temporary_html_file(
    env: jinja2.Environment, template_name: str, context: dict[str, Any]
) -> Path:
    """Render the specified template into a temporary HTML file."""
    html_content = _render_html(env, template_name, context)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as file:
        file.write(html_content.encode("utf-8"))
        return Path(file.name)


def _render_pdf(
    html_content: str, pdf_path: str, env: jinja2.Environment, context: dict[str, Any]
) -> None:
    # Render the cover page and footer content into temporary HTML files. This is needed
    # because the HTML for these can only be passed to wkhtmltopdf as a file path, not
    # as a string. The main body of the page _can_ be passed as a string though.
    cover_html_file = _render_temporary_html_file(env, "cover.jinja2", context)
    logger.debug("Rendered cover HTML to {}", cover_html_file)
    try:
        footer_html_file = _render_temporary_html_file(env, "footer.jinja2", context)
        logger.debug("Rendered footer HTML to {}", footer_html_file)
        pdfkit.from_string(
            html_content,
            pdf_path,
            options={
                "enable-forms": True,
                "enable-local-file-access": True,  # Needed for local images
                "footer-html": footer_html_file,
                "margin-top": "10mm",  # Default margins get set to 0 when footer added
                "margin-bottom": "10mm",
            },
            cover=str(cover_html_file),
            cover_first=True,
            toc={"toc-header-text": "Table of Contents"},
        )
    finally:
        # Ensure the temporary files are always deleted
        cover_html_file.unlink(missing_ok=True)
        logger.debug("Deleted cover HTML file {}", cover_html_file)
        footer_html_file.unlink(missing_ok=True)
        logger.debug("Deleted footer HTML file {}", footer_html_file)
