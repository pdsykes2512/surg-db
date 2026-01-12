from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from motor.motor_asyncio import AsyncIOMotorDatabase

from .database import Database
from .models.user import User, UserInDB, TokenData, UserRole
from .config import settings


# System database dependency
def get_system_database():
    """Get system database for dependency injection"""
    return Database.get_system_database()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# JWT settings
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[UserInDB]:
    """Get a user by email"""
    user_doc = await db.users.find_one({"email": email})
    if user_doc:
        user_doc["_id"] = str(user_doc["_id"])  # Convert ObjectId to string
        return UserInDB(**user_doc)
    return None


async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user by email and password"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
) -> dict:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        
        if email is None:
            raise credentials_exception
        
        # Ensure this is an access token, not a refresh token
        if token_type != "access":
            raise credentials_exception
            
        token_data = TokenData(email=email, role=payload.get("role"), token_type=token_type)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    # Update last login
    await db.users.update_one(
        {"email": email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Return dict with keys expected by audit logging
    return {
        "user_id": user.id,
        "username": user.email,  # Using email as username
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "department": user.department,
        "job_title": user.job_title,
        "created_at": user.created_at,
        "last_login": datetime.utcnow()
    }


async def verify_refresh_token(
    refresh_token: str,
    db: AsyncIOMotorDatabase
) -> Optional[UserInDB]:
    """Verify refresh token and return user"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        
        if email is None or token_type != "refresh":
            return None
            
        user = await get_user_by_email(db, email=email)
        if user is None or not user.is_active:
            return None
            
        return user
    except JWTError:
        return None


def require_role(required_roles: list[UserRole]):
    """Dependency to require specific roles"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}"
            )
        return current_user
    return role_checker


# Common role dependencies
def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_surgeon_or_admin(current_user: dict = Depends(get_current_user)):
    """Require surgeon or admin role"""
    if current_user["role"] not in [UserRole.SURGEON, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Surgeon or admin access required"
        )
    return current_user


def require_data_entry_or_higher(current_user: dict = Depends(get_current_user)):
    """Require data_entry, surgeon, or admin role"""
    if current_user["role"] not in [UserRole.DATA_ENTRY, UserRole.SURGEON, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data entry access or higher required"
        )
    return current_user
