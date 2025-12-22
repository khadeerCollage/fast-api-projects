from pydantic import BaseModel


class postCreate(BaseModel):
    title: str
    content: str

class postresponse(BaseModel):
    title: str
    content: str
    