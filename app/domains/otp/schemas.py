from pydantic import BaseModel

class OTPResponse(BaseModel):
    status: bool
