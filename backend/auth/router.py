from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.auth.schemas import (
    LoginRequest,
    Token,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRole
)
from backend.auth.models import UserModel
from backend.auth.service import AuthService
from backend.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and issue JWT access token"
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticates username or email against stored password hash.
    Issues HS256 signed JWT access token.
    """
    input_str = payload.username_or_email.strip()
    user = db.query(UserModel).filter(
        (UserModel.username == input_str) | (UserModel.email == input_str)
    ).first()

    if not user or not AuthService.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token_str = AuthService.create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )

    return Token(
        access_token=token_str,
        token_type="bearer",
        expires_in=86400,
        role=UserRole(user.role)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get details of currently authenticated user"
)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=UserRole(current_user.role),
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )


# ---------------------------------------------------------------------------
# ADMIN ONLY USER MANAGEMENT ENDPOINTS
# ---------------------------------------------------------------------------

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user account (Admin Restricted)"
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_role([UserRole.ADMIN]))
):
    existing = db.query(UserModel).filter(
        (UserModel.username == payload.username) | (UserModel.email == payload.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    new_user = UserModel(
        username=payload.username.strip(),
        email=payload.email.strip(),
        password_hash=AuthService.hash_password(payload.password),
        role=payload.role.value,
        is_active=payload.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=UserRole(new_user.role),
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat()
    )


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all user accounts (Admin Restricted)"
)
def list_users(
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_role([UserRole.ADMIN]))
):
    users = db.query(UserModel).order_by(UserModel.id.asc()).all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=UserRole(u.role),
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None
        )
        for u in users
    ]


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user role or active status (Admin Restricted)"
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_role([UserRole.ADMIN]))
):
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")

    if payload.email:
        target_user.email = payload.email.strip()
    if payload.role:
        target_user.role = payload.role.value
    if payload.is_active is not None:
        target_user.is_active = payload.is_active
    if payload.password:
        target_user.password_hash = AuthService.hash_password(payload.password)

    db.commit()
    return UserResponse(
        id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        role=UserRole(target_user.role),
        is_active=target_user.is_active,
        created_at=target_user.created_at.isoformat(),
        last_login_at=target_user.last_login_at.isoformat() if target_user.last_login_at else None
    )


@router.delete(
    "/users/{user_id}",
    summary="Deactivate user account (Admin Restricted)"
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_role([UserRole.ADMIN]))
):
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")

    if target_user.id == admin_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete or deactivate self")

    target_user.is_active = False
    db.commit()
    return {"status": "success", "message": f"User {target_user.username} deactivated"}
