from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    process_id: int
    material_id: int
    trigger: str = Field(default="manual", pattern="^(manual|schedule|dry_run)$")


class RunCancelRequest(BaseModel):
    note: str = ""
