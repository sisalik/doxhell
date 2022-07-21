import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(params=[Path("examples") / "example-project"])
def _use_directory(request):
    """Fixture for (temporarily) changing the current working directory.

    The target directory can be specified via parametrization:
    ```
    @pytest.mark.parametrize(
        "_use_directory",
        [Path("examples") / "example-project"],
        indirect=True,
    )
    ```
    """
    original_directory = os.getcwd()
    try:
        os.chdir(request.param)
        yield
    finally:
        os.chdir(original_directory)


@pytest.fixture(params=[{"suffix": ".pdf"}])
def temporary_file(request):
    """Fixture for creating a temporary file.

    The suffix of the file can be specified via parametrization:
    ```
    @pytest.mark.parametrize(
        "temporary_file",
        [{"suffix": ".html"}],
        indirect=True,
    )
    ```
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(
            suffix=request.param["suffix"], delete=False
        )
        temp_file.close()
        temp_file_path = Path(temp_file.name)
        yield temp_file_path
    finally:
        temp_file_path.unlink()
