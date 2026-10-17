from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _clean_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _validate_timezone(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("timezone must not be blank")
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return cleaned


class EmployeeCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    shift_id: int | None = Field(default=None, ge=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _clean_text(value, "full_name")


class EmployeeUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    shift_id: int | None = Field(default=None, ge=1)
    is_active: bool | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str:
        if value is None:
            raise ValueError("email cannot be null")
        return str(value).strip().lower()

    @field_validator("full_name", mode="before")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("full_name cannot be null")
        return _clean_text(value, "full_name")

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("password cannot be null")
        return value

    @field_validator("is_active", mode="before")
    @classmethod
    def validate_active(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("is_active cannot be null")
        return value

    @model_validator(mode="after")
    def require_a_change(self) -> "EmployeeUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one employee field must be provided")
        return self


class EmployeeStatusUpdate(BaseModel):
    is_active: bool


class ShiftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_time: time
    end_time: time
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _clean_text(value, "name")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return _validate_timezone(value)

    @model_validator(mode="after")
    def validate_times(self) -> "ShiftCreate":
        if self.start_time == self.end_time:
            raise ValueError("start_time and end_time must be different")
        return self


class ShiftUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    start_time: time | None = None
    end_time: time | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return _clean_text(value, "name")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_time(cls, value: time | None) -> time:
        if value is None:
            raise ValueError("time fields cannot be null")
        return value

    @field_validator("timezone", mode="before")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("timezone cannot be null")
        return _validate_timezone(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def validate_active(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("is_active cannot be null")
        return value

    @model_validator(mode="after")
    def validate_update(self) -> "ShiftUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one shift field must be provided")
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time == self.end_time
        ):
            raise ValueError("start_time and end_time must be different")
        return self


class ShiftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_time: time
    end_time: time
    timezone: str
    is_active: bool
