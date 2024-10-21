from fastapi import APIRouter , status , Depends
from .schemas import UserCreateModel, UserModel, UserLoginModel
from .service import UserService
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from typing import Annotated
from fastapi.exceptions import  HTTPException
from .utils import create_access_token, decode_token, verify_password
from fastapi.responses import JSONResponse
from datetime import timedelta

user_service = UserService()
auth_router = APIRouter()

MyAsyncSession = Annotated[AsyncSession, Depends(get_session)]

REFRESH_TOKEN_EXPIRY=7

@auth_router.post('/signup' , response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user_account(user_data : UserCreateModel , session : MyAsyncSession ):
    email = user_data.email
    is_exist = await user_service.user_exists_by_email(email , session)
    if is_exist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User with email already exists")
    new_user = await user_service.create_user(user_data, session)
    return new_user

@auth_router.post('/login')
async def login_users(login_data: UserLoginModel, session : MyAsyncSession):
    email = login_data.email
    password = login_data.password
    is_exist = await user_service.user_exists_by_email(email, session)
    if is_exist:
        user = await user_service.get_user_by_email(email,session)
        hashed_password_in_database = user.password_hash
        is_password_true = verify_password(password, hashed_password_in_database )
        if is_password_true:
            access_token = create_access_token(
                user_data= {'email' : user.email, 'user_uid' : str(user.uid)}
            )
            refresh_token = create_access_token(
                user_data= {'email' : user.email, 'user_uid' : str(user.uid)},
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
            )
            return JSONResponse(
                content={
                    "message":"Login succesfull",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "email":user.email,
                        "uid":str(user.uid)
                    }
                }
            )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid email or password")