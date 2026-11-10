from datetime import date

from pydantic import BaseModel, Field


class MaterialCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=128)
    credit_code: str = Field(min_length=1, max_length=32)
    contact: str = ""
    attachments: list[str] = []
    validity_date: date | None = None
    missing_flags: list[str] = []
