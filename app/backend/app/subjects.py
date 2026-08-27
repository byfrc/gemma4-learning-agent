from __future__ import annotations

from dataclasses import dataclass


DEFAULT_SUBJECT = "ai"


@dataclass(frozen=True)
class SubjectSpec:
    key: str
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str


SUBJECT_SPECS: dict[str, SubjectSpec] = {
    "ai": SubjectSpec(
        key="ai",
        label_zh="人工智能",
        label_en="AI",
        description_zh="人工智能课程与学习助手",
        description_en="AI learning track",
    ),
    "java": SubjectSpec(
        key="java",
        label_zh="Java",
        label_en="Java",
        description_zh="Java 语言、面向对象与工程实践",
        description_en="Java language and engineering practice",
    ),
}


def normalize_subject(subject: str | None) -> str:
    value = (subject or "").strip().lower()
    return value if value in SUBJECT_SPECS else DEFAULT_SUBJECT


def get_subject_spec(subject: str | None) -> SubjectSpec:
    return SUBJECT_SPECS[normalize_subject(subject)]


def list_subject_specs() -> list[SubjectSpec]:
    return list(SUBJECT_SPECS.values())


def subject_label(subject: str | None, language: str = "zh") -> str:
    spec = get_subject_spec(subject)
    return spec.label_en if language == "en" else spec.label_zh


def subject_description(subject: str | None, language: str = "zh") -> str:
    spec = get_subject_spec(subject)
    return spec.description_en if language == "en" else spec.description_zh
