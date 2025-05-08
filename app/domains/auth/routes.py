from fastapi import APIRouter, Depends, HTTPException
from app.domains.auth.jwt_service import JWTService
from app.domains.otp.otp_service import OTPService
from fastapi import Request
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])
jwt_service = JWTService()

class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp: str

@router.post("/verify-otp")
async def verify_otp_and_login(request_data: OTPVerifyRequest, request: Request):
    otp_service = request.app.state.otp_service
    
    # Verify OTP
    is_valid = otp_service.verify_otp(request_data.phone_number, request_data.otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Generate JWT token
    access_token = jwt_service.create_access_token(request_data.phone_number)
    
    return {"access_token": access_token, "token_type": "bearer"}