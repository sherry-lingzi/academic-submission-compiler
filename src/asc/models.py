from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Confidence(str, Enum):
    explicit = "explicit"
    inferred = "inferred"
    unknown = "unknown"


class Provenance(BaseModel):
    source: str
    page: int | None = None
    section: str | None = None
    evidence: str


class FontSpec(BaseModel):
    east_asia: str | None = None
    latin: str | None = None
    complex_script: str | None = None


class SizeSpec(BaseModel):
    chinese_name: str | None = None
    pt: float


class RuleCandidate(BaseModel):
    value: Any
    source: str
    provenance: Provenance | None = None


class StyleRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font: FontSpec | None = None
    size: SizeSpec | None = None
    bold: bool | None = None
    italic: bool | None = None
    alignment: Literal["left", "center", "right", "justify"] | None = None
    first_line_indent_chars: float | None = None
    hanging_indent_chars: float | None = None
    line_spacing: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    keep_with_next: bool | None = None
    pagination: str | None = None
    numbering: str | None = None
    separator: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown
    candidates: list[RuleCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def provenance_required(self) -> "StyleRule":
        if self.confidence in {Confidence.explicit, Confidence.inferred} and not self.provenance:
            raise ValueError("explicit/inferred rules require provenance")
        return self

    @property
    def conflicted(self) -> bool:
        return len(self.candidates) > 1


class JournalInfo(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    language: str = "zh-CN"
    test_only: bool = False


class Margins(BaseModel):
    top_mm: float
    bottom_mm: float
    left_mm: float
    right_mm: float


class DocumentRule(BaseModel):
    page_size: Literal["A4", "Letter"] = "A4"
    margins: Margins
    text_color: str = Field(default="000000", pattern=r"^[0-9A-Fa-f]{6}$")
    line_spacing: float | None = None
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown


class CountConstraint(BaseModel):
    minimum: int | None = None
    maximum: int | None = None
    unit: Literal["words", "characters", "items"] = "items"
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown


class AnonymousReviewRule(BaseModel):
    required: bool = False
    hide_authors: bool = True
    hide_affiliations: bool = True
    hide_funding: bool = True
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown


class CitationRule(BaseModel):
    default_mode: Literal["static", "live-zotero"] = "static"
    bibliography: str = "bibliography/references.json"
    csl: str = "citation.csl"
    zotero_style: str | None = None
    locale: str = "zh-CN"
    allow_csl_m_static: bool = False


class OutputRule(BaseModel):
    reference_docx: str = "reference.docx"
    filename_pattern: str = "{manuscript}-{journal}.docx"


class JournalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: Literal["1.0"] = "1.0"
    journal: JournalInfo
    document: DocumentRule
    title: StyleRule = Field(default_factory=StyleRule)
    authors: StyleRule = Field(default_factory=StyleRule)
    affiliations: StyleRule = Field(default_factory=StyleRule)
    abstract: StyleRule = Field(default_factory=StyleRule)
    keywords: StyleRule = Field(default_factory=StyleRule)
    body: StyleRule = Field(default_factory=StyleRule)
    headings: dict[Literal["level1", "level2", "level3"], StyleRule] = Field(default_factory=dict)
    footnotes: StyleRule = Field(default_factory=StyleRule)
    bibliography: StyleRule = Field(default_factory=StyleRule)
    funding: StyleRule = Field(default_factory=StyleRule)
    figures: StyleRule = Field(default_factory=StyleRule)
    tables: StyleRule = Field(default_factory=StyleRule)
    anonymous_review: AnonymousReviewRule = Field(default_factory=AnonymousReviewRule)
    word_count: CountConstraint | None = None
    abstract_count: CountConstraint | None = None
    keyword_count: CountConstraint | None = None
    citation: CitationRule = Field(default_factory=CitationRule)
    output: OutputRule = Field(default_factory=OutputRule)

    def conflicts(self) -> list[str]:
        found: list[str] = []
        for name in ("title", "authors", "affiliations", "abstract", "keywords", "body", "footnotes", "bibliography", "funding", "figures", "tables"):
            if getattr(self, name).conflicted:
                found.append(name)
        found.extend(f"headings.{name}" for name, rule in self.headings.items() if rule.conflicted)
        return found


def load_profile(path: Path) -> JournalProfile:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"profile must be a YAML mapping: {path}")
    return JournalProfile.model_validate(data)


def dump_profile(profile: JournalProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json", exclude_none=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
