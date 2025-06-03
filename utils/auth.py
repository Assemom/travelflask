import os
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET')
ALGORITHM = 'HS512'

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None 