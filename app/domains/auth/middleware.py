from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.domains.auth.jwt_service import JWTService

class JWTAuthMiddleware(HTTPBearer):
    def __init__(self):
        super(JWTAuthMiddleware, self).__init__()
        self.jwt_service = JWTService()

    async def __call__(self, request: Request) -> str:
        credentials: HTTPAuthorizationCredentials = await super(JWTAuthMiddleware, self).__call__(request)

        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
        
        phone_number = self.jwt_service.verify_token(credentials.credentials)
        if not phone_number:
            raise HTTPException(status_code=401, detail="Invalid token or expired token.")
            
        # Verify phone_number in URL matches token (if present)
        url_phone = request.query_params.get('phone_number')
        if url_phone and url_phone != phone_number:
            raise HTTPException(status_code=403, detail="Unauthorized access to this resource.")
            
        return phone_number