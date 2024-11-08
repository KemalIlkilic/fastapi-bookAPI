from fastapi import APIRouter , status , Depends, BackgroundTasks

from ..mail import create_message, mail
from .schemas import UserCreateModel, UserModel, UserLoginModel, UserBooksModel, EmailModel, PasswordResetRequestModel, PasswordResetConfirmModel
from .service import UserService
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from typing import Annotated
from fastapi.exceptions import  HTTPException
from .utils import create_access_token, decode_token, verify_password, create_url_safe_token, decode_url_safe_token, generate_password_hash
from fastapi.responses import JSONResponse
from datetime import timedelta, datetime
from .dependencies import RefreshTokenBearer, AccessTokenBearer, get_current_user, RoleChecker
from src.db.redis import add_jti_to_blocklist
from src.errors import UserAlreadyExists, UserNotFound, InvalidCredentials, InvalidToken
from ..config import Config
from src.db.models import User
from ..celery_tasks import send_email


user_service = UserService()
auth_router = APIRouter()
refresh_token_bearer = RefreshTokenBearer()
access_token_bearer = AccessTokenBearer()


MyAsyncSession = Annotated[AsyncSession, Depends(get_session)]
RefreshTokenDetails = Annotated[dict,Depends(refresh_token_bearer)]
AccessTokenDetails = Annotated[dict,Depends(access_token_bearer)]

# Instance creation - __init__ runs immediately
AdminOnly = Annotated[bool, Depends(RoleChecker(["admin"]))]
UserAndAdmin = Annotated[bool, Depends(RoleChecker(["admin", "user"]))]


REFRESH_TOKEN_EXPIRY=7



@auth_router.post("/send_mail")
async def send_mail(emails: EmailModel):
    emails = emails.addresses

    html = "<h1>Welcome to the app</h1>"
    subject = "Welcome to our app"

    """ message = create_message(recipients=emails, subject=subject, body=html)
    await mail.send_message(message) """
    send_email.delay(emails,subject,html)

    return {"message": "Email sent successfully"}

@auth_router.post('/signup', status_code=status.HTTP_201_CREATED)
async def create_user_account(user_data : UserCreateModel , bg_tasks : BackgroundTasks, session : MyAsyncSession ):
    email = user_data.email
    is_exist = await user_service.user_exists_by_email(email , session)
    if is_exist:
        # This:
        raise UserAlreadyExists()
        # Gets caught by FastAPI, which then:
        # 1. Sees it's a UserAlreadyExists exception
        # 2. Looks up the registered handler
        # 3. Returns the pre-defined response:
    new_user = await user_service.create_user(user_data, session)

    token = create_url_safe_token({"email": email})
    link = f"http://{Config.DOMAIN}/api/v1/auth/verify/{token}"

    html = f"""
    <h1>Verify your Email</h1>
    <p>Please click this <a href="{link}">link</a> to verify your email</p>
    """

    emails = [email]

    subject = "Verify Your email"

    send_email.delay(emails,subject,html)

    return {
        "message": "Account Created! Check email to verify your account",
        "user": new_user,
    }


@auth_router.get('/verify/{token}')
async def get_token(token : str, session : MyAsyncSession):
    token = decode_url_safe_token(token)
    mail = token.get("email")
    if mail:
        user = await user_service.get_user_by_email(mail , session)
        if not user:
            raise UserNotFound()
        user.sqlmodel_update({'is_verified' : True})
        session.add(user)
        await session.commit()
        session.refresh(user)
        return JSONResponse(
            content={"message": "Account verified successfully"},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"message": "Error occured during verification"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

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
                user_data= {'email' : user.email, 'user_uid' : str(user.uid), "role" : user.role}
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
    raise InvalidCredentials()


@auth_router.get('/refresh_token')
async def get_new_access_token(token_details : RefreshTokenDetails):
    expiry_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(user_data=token_details["user"])
        return JSONResponse(content={"access_token": new_access_token})
    raise InvalidToken()

@auth_router.get("/me", response_model=UserBooksModel)
async def get_current_user(authorized : UserAndAdmin ,user = Depends(get_current_user)):
    #RoleChecker Instance's __call__ runs when this endpoint is accessed
    """__call__ executes:
    When the instance is used as a function
    When FastAPI actually needs to check the authorization
    For each request to a protected endpoint
    Not during instance creation or dependency setup
    """
    return user


@auth_router.get("/logout")
async def revooke_token(token_details : AccessTokenDetails):
    jti = token_details["jti"]

    await add_jti_to_blocklist(jti)

    return JSONResponse(
        content={"message": "Logged Out Successfully"}, status_code=status.HTTP_200_OK
    )



@auth_router.post("/password-reset-request")
async def password_reset_request(email_data: PasswordResetRequestModel):
    email = email_data.email

    token = create_url_safe_token({"email": email})

    link = f"http://{Config.DOMAIN}/api/v1/auth/password-reset-confirm/{token}"

    html_message = f"""
    <h1>Reset Your Password</h1>
    <p>Please click this <a href="{link}">link</a> to Reset Your Password</p>
    """
    subject = "Reset Your Password"

    emails = [email]
    message = create_message(recipients=emails, subject=subject, body=html_message)
    await mail.send_message(message)

    return JSONResponse(
        content={
            "message": "Please check your email for instructions to reset your password",
        },
        status_code=status.HTTP_200_OK,
    )




@auth_router.post("/password-reset-confirm/{token}")
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirmModel,
    session: MyAsyncSession,
):
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )

    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")
    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()
        
        passwd_hash = generate_password_hash(new_password)

        user.sqlmodel_update({"password_hash": passwd_hash})
        session.add(user)
        await session.commit()
        session.refresh(user)

        return JSONResponse(
            content={"message": "Password reset Successfully"},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"message": "Error occured during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )