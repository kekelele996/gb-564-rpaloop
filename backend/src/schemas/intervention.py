from pydantic import BaseModel, Field


class InterventionResolveRequest(BaseModel):
    action: str = Field(pattern="^(retry|skip|relocate|abort)$")
    resolution: str = Field(default="", max_length=500)
