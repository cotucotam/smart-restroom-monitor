from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserLogin, UserChangePassword, UserOut
from services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Set session cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "must_change_password": user.must_change_password
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Đăng xuất thành công"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/change-password")
def change_password(
    payload: UserChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác"
        )
    
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}
