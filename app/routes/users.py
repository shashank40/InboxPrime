from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.auth import get_current_active_user, get_current_admin_user, get_password_hash
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import User as UserSchema, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information
    """
    # Update fields
    if user_update.email is not None:
        # Check if email is already used
        if db.query(User).filter(User.email == user_update.email).first() and user_update.email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email
    
    if user_update.username is not None:
        # Check if username is already used
        if db.query(User).filter(User.username == user_update.username).first() and user_update.username != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        current_user.username = user_update.username
    
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.company is not None:
        current_user.company = user_update.company
    
    # Commit changes
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/", response_model=List[UserSchema], dependencies=[Depends(get_current_admin_user)])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema, dependencies=[Depends(get_current_admin_user)])
async def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserSchema, dependencies=[Depends(get_current_admin_user)])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.email is not None:
        # Check if email is already used
        if db.query(User).filter(User.email == user_update.email).first() and user_update.email != user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    if user_update.username is not None:
        # Check if username is already used
        if db.query(User).filter(User.username == user_update.username).first() and user_update.username != user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        user.username = user_update.username
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.company is not None:
        user.company = user_update.company
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    # Commit changes
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin_user)])
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Delete user by ID (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {"status": "success"} 