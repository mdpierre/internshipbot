from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader

from app.schemas.profiles import (
    ProfileEducationInput,
    ProfileExperienceInput,
    ProfileSlotUpdate,
)

SECTION_HEADERS = [
    "summary",
    "objective",
    "profile",
    "about",
    "experience",
    "work experience",
    "work history",
    "employment",
    "professional experience",
    "education",
    "academic background",
    "academic history",
    "skills",
    "technical skills",
    "core competencies",
    "projects",
    "certifications",
    "awards",
    "languages",
    "references",
    "contact",
]


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {"_header": ""}
    current = "_header"
    header_re = re.compile(rf"^\s*({'|'.join(re.escape(h) for h in SECTION_HEADERS)})\s*[:\-]?\s*$", re.I)
    for line in text.splitlines():
        match = header_re.match(line)
        if match:
            current = match.group(1).lower().strip()
            sections[current] = ""
        else:
            sections[current] = (sections.get(current, "") + line + "\n").strip("\n") + "\n"
    return sections


def get_section(sections: dict[str, str], *keys: str) -> str:
    for key in keys:
        for section_key, content in sections.items():
            if key in section_key and content.strip():
                return content
    return ""


def extract_name(text: str) -> tuple[str, str, str]:
    for line in [line.strip() for line in text.splitlines()[:6]]:
        if not line or "@" in line or "http" in line or re.search(r"\d{3}", line):
            continue
        parts = line.split()
        if 2 <= len(parts) <= 4 and all(re.match(r"^[A-Z][a-zA-Z' -]+$", p) for p in parts):
            full_name = " ".join(parts)
            return parts[0], parts[-1], full_name
    return "", "", ""


def extract_contact(text: str) -> dict[str, str]:
    email = re.search(r"[\w.+%-]+@[\w-]+\.[a-zA-Z]{2,7}", text)
    phone = re.search(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    linkedin = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[\w%-/]+)", text, re.I)
    github = re.search(r"(https?://(?:www\.)?github\.com/[\w%-/]+)", text, re.I)
    website = re.search(r"https?://(?!(?:www\.)?(?:linkedin|github)\.com)[\w.-]+\.[a-z]{2,}[^\s,)]*", text, re.I)
    city_state = re.search(r"([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})(?:\s+(\d{5}(?:-\d{4})?))?", text)
    return {
        "email": email.group(0).lower() if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "linkedin": linkedin.group(1) if linkedin else "",
        "github": github.group(1) if github else "",
        "website": website.group(0) if website else "",
        "city": city_state.group(1).strip() if city_state else "",
        "state": city_state.group(2).strip() if city_state else "",
        "zip": city_state.group(3).strip() if city_state and city_state.group(3) else "",
    }


def extract_educations(education_text: str) -> list[ProfileEducationInput]:
    if not education_text.strip():
        return []
    school_match = re.search(r"([A-Z][^\n]*(?:University|College|Institute|School|Academy)[^\n,]*)", education_text, re.I)
    degree_match = re.search(
        r"(Bachelor(?:'s)?|Master(?:'s)?|PhD|Doctor|Associate(?:'s)?|B\.S\.|B\.A\.|M\.S\.|M\.B\.A\.?|MBA)[^\n]*",
        education_text,
        re.I,
    )
    grad_year_match = re.search(r"(?:expected|graduating|graduation)[:\s]*(?:May|June|December|Spring|Fall)?\s*(20\d{2})", education_text, re.I)
    if not grad_year_match:
        grad_year_match = re.search(r"\b(20\d{2})\b", education_text)
    major_match = re.search(r"(?:Major|Concentration|Field)[:\s]+([^\n,]+)", education_text, re.I)
    gpa_match = re.search(r"(?:GPA|Grade Point Average)[:\s]+(\d\.\d{1,2})", education_text, re.I)

    return [
        ProfileEducationInput(
            school=school_match.group(1).strip() if school_match else "",
            degree=degree_match.group(0).strip() if degree_match else "",
            major=major_match.group(1).strip() if major_match else "",
            graduation_year=grad_year_match.group(1) if grad_year_match else "",
            gpa=gpa_match.group(1) if gpa_match else "",
        )
    ]


def extract_experiences(experience_text: str) -> list[ProfileExperienceInput]:
    if not experience_text.strip():
        return []
    lines = [line.strip() for line in experience_text.splitlines() if line.strip()]
    date_re = re.compile(r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?\d{4}\s*(?:-|–|—|to)\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?\d{4}|present|current|now", re.I)
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if date_re.search(line) and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    results: list[ProfileExperienceInput] = []
    for block in blocks[:5]:
        title = block[0] if block else ""
        employer = block[1] if len(block) > 1 else ""
        date_line = next((line for line in block if date_re.search(line)), "")
        date_parts = re.split(r"\s*(?:-|–|—|to)\s*", date_line, maxsplit=1) if date_line else ["", ""]
        description_lines = [line for line in block[2:] if line != date_line]
        results.append(
            ProfileExperienceInput(
                employer=employer[:255],
                title=title[:255],
                start_date=date_parts[0][:32] if date_parts else "",
                end_date=date_parts[1][:32] if len(date_parts) > 1 else "",
                location="",
                description=" ".join(description_lines)[:2000],
            )
        )
    return results


def parse_resume_to_profile(text: str, display_name: str, resume_label: str) -> ProfileSlotUpdate:
    sections = split_sections(text)
    first_name, last_name, full_name = extract_name(sections.get("_header", text))
    contact = extract_contact(text)
    experiences = extract_experiences(get_section(sections, "experience", "employment", "work history"))
    educations = extract_educations(get_section(sections, "education", "academic"))

    return ProfileSlotUpdate(
        display_name=display_name,
        profile_name=display_name,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        email=contact["email"],
        phone=contact["phone"],
        city=contact["city"],
        state=contact["state"],
        zip=contact["zip"],
        linkedin=contact["linkedin"],
        website=contact["website"],
        github=contact["github"],
        resume_label=resume_label,
        experiences=experiences,
        educations=educations,
    )
