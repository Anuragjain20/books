from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from app_base.utils import get_client_ip
from app_accounts.models import CustomerModel
from .models import *
from .threads import *
from .serializer import *

@api_view(["POST"])
def signUp(request):
    try:
        data = request.data
        serializer = signupSerializer(data=data)
        if serializer.is_valid():
            name = serializer.data["name"]
            email = serializer.data["email"]
            password = serializer.data["password"]
            if CustomerModel.objects.filter(email=email).first():
                return Response({"result":"Acount already exists."}, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                new_customer = CustomerModel.objects.create(email=email, name=name)
                new_customer.set_password(password)
                thread_obj = send_verification_email(email)
                thread_obj.start()
                new_customer.save()
                return Response({"result":"Account created, verification mail sent"}, status=status.HTTP_201_CREATED)
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error":e, "message":"Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def verify(request):
    try:
        data = request.data
        serializer = otpSerializer(data=data)
        if serializer.is_valid():
            otp = serializer.data["otp"]
            if not cache.get(otp):
                return Response({"result":"OTP expired"}, status=status.HTTP_408_REQUEST_TIMEOUT)
            user_obj = CustomerModel.objects.filter(email=cache.get(otp)).first()
            if user_obj:
                if user_obj.is_verified:
                    return Response({"result":"Account is already verified"}, status=status.HTTP_412_PRECONDITION_FAILED)
                user_obj.is_verified = True
                user_obj.save()
                return Response({"result":"Account verification successfull"}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        return Response({"error":e, "message":"Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def logIn(request):
    try:
        data = request.data
        serializer = loginSerializer(data=data)
        if serializer.is_valid():
            email = serializer.data["email"]
            password = serializer.data["password"]
            customer_obj = CustomerModel.objects.filter(email=email).first()
            if customer_obj is None:
                return Response({"result":"Account does not exist"}, status=status.HTTP_404_NOT_FOUND)
            if not customer_obj.is_verified:
                return Response({"result":"Email not verified. Check your mail"}, status=status.HTTP_401_UNAUTHORIZED)
            user = authenticate(email=email, password=password)
            if not user:
                return Response({"result":"Incorrect password"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            jwt_token = RefreshToken.for_user(user)
            return Response({"result":"Login successfull", "token":str(jwt_token.access_token)}, status=status.HTTP_202_ACCEPTED)
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error":e, "message":"Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def forgot(request):
    try:
        data = request.data
        serializer = emailSerializer(data=data)
        if serializer.is_valid():
            email = serializer.data["email"]
            if not CustomerModel.objects.get(email=email):
                return Response({"result":"Account does not exists"}, status=status.HTTP_404_NOT_FOUND)
            thread_obj = send_forgot_link(email)
            thread_obj.start()
            return Response({"result":"reset mail sent"}, status=status.HTTP_200_OK)
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error":e, "message":"Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def reset(request):
    try:
        data = request.data
        serializer = otpSerializer(data=data)
        if serializer.is_valid():
            otp = serializer.data["otp"]
            if not cache.get(otp):
                return Response({"result":"OTP expired"}, status=status.HTTP_408_REQUEST_TIMEOUT)
            if not CustomerModel.objects.filter(email=cache.get(otp)).first():
                return Response({"message":"user does not exist"}, status=status.HTTP_404_NOT_FOUND)
            user_obj = CustomerModel.objects.get(email=cache.get(otp))
            npw = serializer.data["npw"]
            cpw = serializer.data["cpw"]
            if npw == cpw:
                user_obj.set_password(cpw)
                user_obj.save()
                return Response({"result":"Password changed successfull"}, status=status.HTTP_202_ACCEPTED)
        else:return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error":e, "message":"Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def resendForgot(request):
    try:
        data = request.data
        current_ip = get_client_ip(request)
        if cache.get(current_ip):
            total_calls = cache.get(current_ip)
            if total_calls > 5 :
                return Response({"message":"Exceeded total no of calls", "time": f"you can try again after {cache.ttl(current_ip)} seconds"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                cache.set(current_ip, total_calls+1)
                serializer = emailSerializer(data=data)
                if serializer.is_valid():
                    email = serializer.data["email"]
                    thread_obj = send_forgot_link(email)
                    thread_obj.start()
                    return Response({"message":"OTP sent on your email", "times":total_calls}, status=status.HTTP_200_OK)
                return Response({"errors":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        cache.set(current_ip, 1, timeout=60)
    except Exception as e:
        return Response({"error":e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def resendVerify(request):
    try:
        data = request.data
        serializer = emailSerializer(data=data)
        current_ip = get_client_ip(request)
        if cache.get(current_ip):
            total_calls = cache.get(current_ip)
            if total_calls > 5 :
                return Response({"message":"Exceeded total no of calls", "time": f"you can try again after {cache.ttl(current_ip)} seconds"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                cache.set(current_ip, total_calls+1)
                if serializer.is_valid():
                    email = serializer.data["email"]
                    thread_obj = send_verification_email(email)
                    thread_obj.start()
                    return Response({"message":"OTP sent on your email"}, status=status.HTTP_200_OK)
                return Response({"errors":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        cache.set(current_ip, 1, timeout=60)
    except Exception as e:
        return Response({"error":e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)