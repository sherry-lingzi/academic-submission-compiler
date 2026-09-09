from __future__ import annotations

from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from asc.capabilities import STYLE_FIELD_CAPABILITIES


class Confidence(str, Enum):
    explicit = "explicit"
    inferred = "inferred"
    user_confirmed = "user_confirmed"
    unknown = "unknown"


class SourceKind(str, Enum):
    journal = "journal"
    template = "template"
    inferred = "inferred"
    system_default = "system_default"
    user_override = "user_override"


class ProfileStatus(str, Enum):
    generated = "generated"
    reviewed = "reviewed"
    approved = "approved"


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
    # Kept for lossless migration. ASC 0.2.0 rejects configured values.
    pagination: str | None = None
    numbering: str | None = None
    separator: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown
    source_kind: SourceKind | None = None
    candidates: list[RuleCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self) -> "StyleRule":
        if self.confidence in {Confidence.explicit, Confidence.inferred, Confidence.user_confirmed} and not self.provenance:
            raise ValueError("explicit/inferred/user_confirmed rules require provenance")
        if self.source_kind is None:
            self.source_kind = {
                Confidence.explicit: SourceKind.journal,
                Confidence.inferred: SourceKind.inferred,
                Confidence.user_confirmed: SourceKind.user_override,
                Confidence.unknown: SourceKind.system_default,
            }[self.confidence]
        return self

    @property
    def conflicted(self) -> bool:
        return len(self.candidates) > 1

    def configured_fields(self) -> list[str]:
        ignored = {"provenance", "confidence", "source_kind", "candidates"}
        return [name for name, value in self.model_dump().items() if name not in ignored and value is not None]

    def unsupported_fields(self) -> list[str]:
        return [name for name, status in STYLE_FIELD_CAPABILITIES.items() if status == "unsupported" and "." not in name and getattr(self, name) is not None]


class LocalizedTitleRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default: StyleRule = Field(default_factory=StyleRule)
    zh: StyleRule | None = None
    en: StyleRule | None = None

    def for_language(self, language: str) -> StyleRule:
        return (self.zh if language == "zh" else self.en) or self.default


class CountConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum: int | None = None
    maximum: int | None = None
    unit: Literal["words", "characters", "items"] = "items"
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown
    source_kind: SourceKind | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "CountConstraint":
        if self.confidence in {Confidence.explicit, Confidence.inferred, Confidence.user_confirmed} and not self.provenance:
            raise ValueError("explicit/inferred/user_confirmed count rules require provenance")
        if self.source_kind is None:
            self.source_kind = {
                Confidence.explicit: SourceKind.journal,
                Confidence.inferred: SourceKind.inferred,
                Confidence.user_confirmed: SourceKind.user_override,
                Confidence.unknown: SourceKind.system_default,
            }[self.confidence]
        return self


class TextVariantRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: StyleRule = Field(default_factory=StyleRule)
    body: StyleRule = Field(default_factory=StyleRule)
    count: CountConstraint | None = None
    separator: str | None = None
    separator_source_kind: SourceKind = SourceKind.system_default
    separator_provenance: Provenance | None = None


class BilingualTextRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zh: TextVariantRule = Field(default_factory=TextVariantRule)
    en: TextVariantRule = Field(default_factory=TextVariantRule)


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
    model_config = ConfigDict(extra="forbid")
    page_size: Literal["A4", "Letter"] = "A4"
    margins: Margins
    text_color: str = Field(default="000000", pattern=r"^[0-9A-Fa-f]{6}$")
    line_spacing: float | None = None
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown
    source_kind: SourceKind | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "DocumentRule":
        if self.confidence in {Confidence.explicit, Confidence.inferred, Confidence.user_confirmed} and not self.provenance:
            raise ValueError("explicit/inferred/user_confirmed document rules require provenance")
        if self.source_kind is None:
            self.source_kind = SourceKind.system_default if self.confidence == Confidence.unknown else SourceKind.journal
        return self


class AnonymousReviewRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    required: bool = False
    hide_authors: bool = True
    hide_affiliations: bool = True
    hide_funding: bool = True
    hide_email: bool = True
    hide_orcid: bool = True
    hide_correspondence: bool = True
    hide_acknowledgements: bool = True
    provenance: Provenance | None = None
    confidence: Confidence = Confidence.unknown
    source_kind: SourceKind | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "AnonymousReviewRule":
        if self.confidence in {Confidence.explicit, Confidence.inferred, Confidence.user_confirmed} and not self.provenance:
            raise ValueError("explicit/inferred/user_confirmed anonymous-review rules require provenance")
        if self.source_kind is None:
            self.source_kind = SourceKind.system_default if self.confidence == Confidence.unknown else SourceKind.journal
        return self


class CitationRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_mode: Literal["static", "live-zotero"] = "static"
    bibliography: str = "bibliography/references.json"
    csl: str = "citation.csl"
    zotero_style: str | None = None
    locale: str = "zh-CN"
    allow_csl_m_static: bool = False


class OutputRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_docx: str = "reference.docx"
    filename_pattern: str = "{manuscript}-{journal}.docx"


class ObsidianRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attachment_paths: list[str] = Field(default_factory=lambda: ["attachments", "assets", "figures"])


class JournalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: Literal["2.0"] = "2.0"
    profile_status: ProfileStatus = ProfileStatus.generated
    approved_at: str | None = None
    journal: JournalInfo
    document: DocumentRule
    title: LocalizedTitleRule = Field(default_factory=LocalizedTitleRule)
    authors: StyleRule = Field(default_factory=StyleRule)
    affiliations: StyleRule = Field(default_factory=StyleRule)
    abstract: BilingualTextRule = Field(default_factory=BilingualTextRule)
    keywords: BilingualTextRule = Field(default_factory=BilingualTextRule)
    body: StyleRule = Field(default_factory=StyleRule)
    headings: dict[Literal["level1", "level2", "level3"], StyleRule] = Field(default_factory=dict)
    footnotes: StyleRule = Field(default_factory=StyleRule)
    bibliography: StyleRule = Field(default_factory=StyleRule)
    funding: StyleRule = Field(default_factory=StyleRule)
    figures: StyleRule = Field(default_factory=StyleRule)
    tables: StyleRule = Field(default_factory=StyleRule)
    anonymous_review: AnonymousReviewRule = Field(default_factory=AnonymousReviewRule)
    word_count: CountConstraint | None = None
    citation: CitationRule = Field(default_factory=CitationRule)
    output: OutputRule = Field(default_factory=OutputRule)
    obsidian: ObsidianRule = Field(default_factory=ObsidianRule)

    def iter_style_rules(self) -> Iterable[tuple[str, StyleRule]]:
        yield "title.default", self.title.default
        if self.title.zh is not None:
            yield "title.zh", self.title.zh
        if self.title.en is not None:
            yield "title.en", self.title.en
        for name in ("authors", "affiliations", "body", "footnotes", "bibliography", "funding", "figures", "tables"):
            yield name, getattr(self, name)
        for language in ("zh", "en"):
            for field in ("abstract", "keywords"):
                variant = getattr(getattr(self, field), language)
                yield f"{field}.{language}.label", variant.label
                yield f"{field}.{language}.body", variant.body
        for name, rule in self.headings.items():
            yield f"headings.{name}", rule

    def conflicts(self) -> list[str]:
        return [name for name, rule in self.iter_style_rules() if rule.conflicted]

    def unsupported_configured(self) -> list[str]:
        return [f"{name}.{field}" for name, rule in self.iter_style_rules() for field in rule.unsupported_fields()]

    def unknown_rules(self) -> list[str]:
        found = [name for name, rule in self.iter_style_rules() if rule.confidence == Confidence.unknown]
        if self.document.confidence == Confidence.unknown:
            found.append("document")
        if self.anonymous_review.confidence == Confidence.unknown:
            found.append("anonymous_review")
        if self.word_count and self.word_count.confidence == Confidence.unknown:
            found.append("word_count")
        for field in ("abstract", "keywords"):
            for language in ("zh", "en"):
                variant = getattr(getattr(self, field), language)
                if variant.count and variant.count.confidence == Confidence.unknown:
                    found.append(f"{field}.{language}.count")
                if variant.separator is not None and variant.separator_source_kind == SourceKind.system_default:
                    found.append(f"{field}.{language}.separator")
        return found

    def coverage(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        rules: list[Any] = [rule for _, rule in self.iter_style_rules()]
        rules.extend([self.document, self.anonymous_review])
        if self.word_count:
            rules.append(self.word_count)
        for field in (self.abstract, self.keywords):
            for variant in (field.zh, field.en):
                if variant.count:
                    rules.append(variant.count)
                if variant.separator is not None:
                    key = "system_default" if variant.separator_source_kind == SourceKind.system_default else variant.separator_source_kind.value
                    counts[key] += 1
        for rule in rules:
            if getattr(rule, "source_kind", None) == SourceKind.system_default:
                counts["system_default"] += 1
            else:
                counts[getattr(rule, "confidence", Confidence.unknown).value] += 1
        counts["conflict"] = len(self.conflicts())
        counts["unsupported"] = len(self.unsupported_configured())
        return counts


def _legacy_variant(style: dict[str, Any], count: dict[str, Any] | None, language: str, keyword: bool) -> dict[str, Any]:
    separator = ("；" if language == "zh" else "; ") if keyword else None
    label = {
        "font": style.get("font"),
        "size": style.get("size"),
        "bold": True,
        "confidence": "unknown",
        "source_kind": "system_default",
    }
    migrated_count = dict(count) if count else None
    if migrated_count and language == "en" and not keyword:
        migrated_count = {
            "minimum": migrated_count.get("minimum"),
            "maximum": migrated_count.get("maximum"),
            "unit": "words",
            "confidence": "unknown",
            "source_kind": "system_default",
        }
    return {
        "label": {key: value for key, value in label.items() if value is not None},
        "body": style,
        "count": migrated_count,
        **({"separator": separator, "separator_source_kind": "system_default"} if keyword else {}),
    }


def migrate_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate Profile 1.0 data to the explicit 2.0 contract in memory."""
    if str(data.get("profile_version", "1.0")) == "2.0":
        return data
    migrated = dict(data)
    migrated["profile_version"] = "2.0"
    legacy_title = migrated.get("title") or {}
    if "default" not in legacy_title and "zh" not in legacy_title and "en" not in legacy_title:
        migrated["title"] = {"default": legacy_title}
    legacy_abstract = migrated.get("abstract") or {}
    legacy_keywords = migrated.get("keywords") or {}
    abstract_count = migrated.pop("abstract_count", None)
    keyword_count = migrated.pop("keyword_count", None)
    if "zh" not in legacy_abstract and "en" not in legacy_abstract:
        migrated["abstract"] = {
            "zh": _legacy_variant(legacy_abstract, abstract_count, "zh", False),
            "en": _legacy_variant(legacy_abstract, abstract_count, "en", False),
        }
    if "zh" not in legacy_keywords and "en" not in legacy_keywords:
        migrated["keywords"] = {
            "zh": _legacy_variant(legacy_keywords, keyword_count, "zh", True),
            "en": _legacy_variant(legacy_keywords, keyword_count, "en", True),
        }
    return migrated


def load_profile(path: Path) -> JournalProfile:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"profile must be a YAML mapping: {path}")
    migrated = migrate_profile_data(data)
    if str(data.get("profile_version", "1.0")) != "2.0":
        migrated["profile_status"] = "approved" if path.name == "profile.yaml" else "generated"
    return JournalProfile.model_validate(migrated)


def dump_profile(profile: JournalProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json", exclude_none=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
