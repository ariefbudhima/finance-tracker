from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/otp")
def send_otp(phone_number: str, request: Request):
    """
    Endpoint to send OTP.
    """
    otp_service = request.app.state.otp_service
    result = otp_service.send_otp(phone_number)
    # Implement the logic to send OTP here
    return {"message": result}

@router.post("/verify")
async def verify_otp(request: Request):
    """
    Endpoint to verify OTP.
    """
    otp_service = request.app.state.otp_service
    result = otp_service.verify_otp(request)

    # Implement the logic to verify OTP here
    return {"message": result}