from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


PROFILE_SLOTS = ("profile_1", "profile_2", "profile_3")


class ProfileExperienceInput(BaseModel):
    employer: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""


class ProfileEducationInput(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    graduation_year: str = ""
    gpa: str = ""


class ProfileSlotUpdate(BaseModel):
    display_name: str
    profile_name: str = ""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "United States"
    linkedin: str = ""
    website: str = ""
    github: str = ""
    target_title: str = ""
    target_salary: str = ""
    work_authorization: str = "Yes - U.S. Citizen or Permanent Resident"
    require_sponsorship: str = "No"
    veteran: str = "No"
    disability: str = "Prefer not to say"
    gender: str = "Prefer not to say"
    ethnicity: str = "Prefer not to say"
    summary: str = ""
    resume_label: str = ""
    is_active: bool = False
    experiences: list[ProfileExperienceInput] = Field(default_factory=list)
    educations: list[ProfileEducationInput] = Field(default_factory=list)


class ProfileExperienceResponse(ProfileExperienceInput):
    model_config = ConfigDict(from_attributes=True)


class ProfileEducationResponse(ProfileEducationInput):
    model_config = ConfigDict(from_attributes=True)


class ProfileSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slot: str
    display_name: str
    profile_name: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    city: str
    state: str
    zip: str
    country: str
    linkedin: str
    website: str
    github: str
    target_title: str
    target_salary: str
    work_authorization: str
    require_sponsorship: str
    veteran: str
    disability: str
    gender: str
    ethnicity: str
    summary: str
    resume_label: str
    resume_filename: str | None
    resume_content_type: str | None
    resume_uploaded_at: datetime | None
    is_active: bool
    experiences: list[ProfileExperienceResponse]
    educations: list[ProfileEducationResponse]
    created_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    slot: str
    resume_label: str
    resume_filename: str
    resume_content_type: str
    resume_uploaded_at: datetime


class ResumeParseResponse(BaseModel):
    slot: str
    parsed_profile: ProfileSlotUpdate
