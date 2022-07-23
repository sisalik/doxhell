import enum
from pathlib import Path
from typing import Iterable, Iterator

from pydantic import BaseModel, validator


class HashableBaseModel(BaseModel):
    """Base model that can be used as a hashable key."""

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))


class Requirement(HashableBaseModel):
    """A requirement found in the documentation."""

    id: str
    specification: str
    rationale: str
    parent: str = ""
    obsolete: bool = False
    obsolete_reason: str = ""


class EvidenceType(str, enum.Enum):
    """The type of evidence used to prove that a manual test passed."""

    SCREENSHOT = "screenshot"
    LOG = "log"
    OBSERVATION = "observation"
    SETTINGS = "settings"


class TestStep(BaseModel):
    """A step in a test."""

    given: str
    when: str
    then: str
    evidence: EvidenceType | None


class Test(BaseModel):
    """A test found in the documentation or automated test module."""

    id: str
    description: str
    verifies: list[str]
    steps: list[TestStep] = []
    automated: bool = False
    file_path: Path | None

    @validator("automated", always=True)
    def steps_must_be_defined_for_manual_test(cls, v, values):
        """Validate that steps are defined if automated is False."""
        if not v and not values["steps"]:
            raise ValueError("steps are required for a manual test")
        return v

    @property
    def full_name(self) -> str:
        """Return the full name of the test."""
        return f"{self.file_path}::{self.id}"


class Section(BaseModel):
    """A section in a document."""

    title: str
    items: list[Requirement]


class BaseDocument(BaseModel):
    """A base class for a document."""

    title: str
    number: str | None
    revision: str | None
    author: str | None
    file_path: Path

    @property
    def full_title(self) -> str:
        """Return the full name of the document."""
        title = ""
        if self.number:
            title += self.number
        if self.revision:
            title += self.revision
        if self.number or self.revision:
            title += " "
        title += self.title
        return title


class RequirementsDoc(BaseDocument):
    """A requirements specification document."""

    # When parsing documents, support a flat list of requirements or a list of sections,
    # each containing a list of requirements. In the former case, they will be grouped
    # under a default section during loading.
    body: list[Requirement] | list[Section]

    @property
    def requirements(self) -> Iterator[Requirement]:
        """Yield all requirements."""
        for section in self.body:
            # By this point, a flat list of requirements must be grouped under a section
            assert isinstance(section, Section), "body must be a list of sections"
            yield from section.items


class CoverageDoc(BaseDocument):
    """A test coverage document."""

    # Mapping of requirements to test populated during later review, not initial parsing
    mapping: dict[Requirement, list[Test]] = {}

    def map(self, requirements: Iterable[Requirement], tests: Iterable[Test]) -> None:
        """Map requirements to tests."""
        tests_list = list(tests)  # If an iterator is passed, it will be consumed
        for requirement in requirements:
            self.mapping[requirement] = []
            for test in tests_list:
                if requirement.id in test.verifies:
                    self.mapping[requirement].append(test)


class TestsDoc(BaseDocument):
    """A manual test protocol document."""

    tests: list[Test]


class TestSuite(BaseModel):
    """A collection of automated and manual tests."""

    manual_tests_doc: TestsDoc | None
    automated_tests: list[Test]

    @property
    def all_tests(self) -> Iterator[Test]:
        """Yield all tests."""
        if self.manual_tests_doc:
            yield from self.manual_tests_doc.tests
        if self.automated_tests:
            yield from self.automated_tests
