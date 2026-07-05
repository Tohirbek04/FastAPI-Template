from pydantic import BaseModel


class Msg(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str
    code: str
