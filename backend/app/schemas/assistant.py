from typing import Any

from pydantic import BaseModel, Field, model_validator


class AssistantQueryRequest(BaseModel):
    query: str = Field(default="", max_length=2000, description="The user's attendance question or request.")
    message: str | None = Field(default=None, max_length=2000, description="Alternative field for user's query.")

    @model_validator(mode="after")
    def validate_query_present(self) -> "AssistantQueryRequest":
        text = (self.query or self.message or "").strip()
        if not text:
            raise ValueError("Query cannot be empty.")
        self.query = text
        return self


class AssistantQueryResponse(BaseModel):
    query: str
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    report_data: dict[str, Any] | None = None
