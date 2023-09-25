from django.shortcuts import render
from django.views.generic import View
from footapp.models import Database
from django.views.decorators.cache import cache_page
from django.core import serializers
from django.http import HttpRequest, JsonResponse
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
import json
from django.utils import timezone
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from django.contrib.auth import authenticate, login
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
import os
import cv2
import io
from imageio import imread
import base64
from django.db.models import Q


_path = Path(__file__, "..").resolve()
# Create your views here.

login_required = login_required(redirect_field_name=None)


# def login_required(handler_func):
#     def decorator(request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return HttpResponseForbidden()

#         return handler_func(request, *args, **kwargs)
#     return decorator


def serialize_data_instances(instances):
    data = serializers.serialize("json", instances)
    data = json.loads(data)
    for entry in data:
        entry["fields"]["id"] = entry["pk"]
    data = list(i["fields"] for i in data)
    data = json.dumps(data)
    return data


@login_required
def get_collection(request: HttpRequest):  # 1)
    SORT_OPTION = ["created_date", "pk", "name"]
    FILTERS_SIDE = ["L", "R"]
    FILTERS_STAT = ["N", "H", "F", "U"]

    filter = request.GET.getlist("filter", None)
    search = request.GET.get("search", None)
    sort = request.GET.get("sort", "pk")
    ascending = json.loads(request.GET.get("ascending", True))

    try:
        start = int(request.GET.get("start"))
        end = int(request.GET.get("end"))
    except:
        return HttpResponseBadRequest()

    # Verify filters
    for i in filter:
        if i not in (FILTERS_SIDE + FILTERS_STAT):
            return HttpResponseBadRequest()

    # Verify sort
    if sort not in SORT_OPTION:
        return HttpResponseBadRequest()

    # Correct start index
    if start < 0:
        start = 0

    if not ascending:
        sort = "-" + sort

    if request.method == "GET":
        instances = Database.objects.all()

        # Create Q Filters
        filterQ = []
        if len(filter) > 0:  # stat & side filter
            for f in filter:
                if f in FILTERS_STAT:
                    filterQ += [Q(stat=f)]
                    if f == "U":
                        filterQ += [Q(stat=None)]
                elif f in FILTERS_SIDE:
                    filterQ += [Q(side=f)]

        if search:
            filterQ += [Q(name__icontains=search)]

        if len(filterQ) > 0:
            # Combine filters
            combinedFilter = filterQ.pop()
            for i in filterQ:
                combinedFilter |= i

            # Apply filters
            instances = instances.filter(combinedFilter)

        try:
            instances = instances.order_by(sort)[start:end]
        except:
            instances = instances.order_by(sort)[start:]

        data = serialize_data_instances(instances)
        return HttpResponse(data, content_type="application/json")


@login_required
def get_collection_by_id(request: HttpRequest, id):
    instance = Database.objects.filter(id=id)
    data = serialize_data_instances(instance)
    return HttpResponse(data, content_type="application/json")


@login_required
def patch_collection(request: HttpRequest):  # 2)
    if request.method == "PATCH":
        try:
            received_json_data = json.loads(request.body)
            Database.objects.filter(id=received_json_data["id"]).update(
                name=received_json_data["name"],
                stat=received_json_data["stat"],
                side=received_json_data["side"],
                remark=received_json_data["remark"],
                deleted=received_json_data["deleted"],
                modify_date=timezone.now(),
            )
            if received_json_data["deleted"] == True:
                Database.objects.filter(id=received_json_data["id"]).update(
                    deleted_date=timezone.now()
                )
            return HttpResponse("Patch successfully!")
        except:
            return HttpResponseBadRequest()


def auth(request: HttpRequest):  # 3)
    if request.method == "POST":
        received_json_data = json.loads(request.body)
        username = received_json_data["username"]
        password = received_json_data["password"]
        print(username)
        print(password)
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            return HttpResponse("Login successfully!")
        else:
            return HttpResponseForbidden()


@login_required
def logout_api(request: HttpRequest):
    logout(request)
    return HttpResponse("Logout successfully!")


# @login_required
def session(request: HttpRequest):
    if request.user.is_authenticated:
        return HttpResponse(request.user.username)

    return HttpResponseForbidden()


# @login_required
# def add_collection(request):
#     if request.method=='POST':
#         received_json_data= json.loads(request.body)
#         try:
#             Database.objects.create(**received_json_data)
#             # Database.save()
#             return HttpResponse('POST successfully!!')
#         except Exception:
#             return HttpResponse('POST successful BUT DID NOT PUT IN DATABASE!!')

#     return HttpResponse('We got request')

@login_required
def add_collection(request: HttpRequest):
    added_id = []
    received_json_data = json.loads(request.body)
    for img_data in received_json_data["img_file"]:
        gauth = GoogleAuth()
        scope = ["https://www.googleapis.com/auth/drive"]
        _path = os.path.dirname(__file__)
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            _path + "\\credential.json", scope
        )
        drive = GoogleDrive(gauth)
        decoded_img = base64.b64decode(img_data)

        file_type = "jpeg"
        if decoded_img.startswith(bytes.fromhex("89504E470D0A1A0A")):
            file_type = "png"
        elif decoded_img.startswith(bytes.fromhex("FFD8FFE0")):
            file_type = "jpeg"

        instance = Database.objects.create(
            owner=request.user.username, file_type=file_type
        )
        data = instance.__dict__
        file_name = "img_" + data["name"] + f".{file_type}"
        _file = drive.CreateFile(
            {
                "parents": [{"id": "1IYdmr-oWqKKCjq-RsjBbS9kEgcnY_G4R"}],
                "title": f"{file_name}",
                "mimeType": f"image/{file_type}",
            }
        )
        with open(_path + f"\\temp.{file_type}", "wb") as fh:
            fh.write(base64.b64decode(img_data))
            fh.close()
        _file.SetContentFile(_path + f"\\temp.{file_type}")
        _file.Upload()
        Database.objects.filter(name=data["name"]).update(link=str(_file["id"]))
        added_id.append(data["id"])
    ids = json.dumps({"ids": added_id})
    print("done", ids)
    return HttpResponse(ids, content_type="application/json")


@login_required
@cache_page(60 * 60 * 24)
def get_img(request: HttpRequest, id: int):
    instance = Database.objects.filter(id=id)
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    _path = os.path.dirname(__file__)
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        _path + "\\credential.json", scope
    )
    drive = GoogleDrive(gauth)
    file_id = instance[0].__dict__["link"]
    file_type = instance[0].__dict__["file_type"] or "jpeg"
    _file = drive.CreateFile({"id": f"{file_id}", "mimeType": f"image/{file_type}"})
    _file.GetContentFile(
        filename=_path + f"\\temp.{file_type}", mimetype=f"image/{file_type}"
    )
    with open(_path + f"\\temp.{file_type}", "rb") as f:
        img = f.read()
        return HttpResponse(img, content_type=f"image/{file_type}")


@login_required
@cache_page(60 * 60 * 24)
def summary(request):
    username = request.user.username
    instances = Database.objects.all()
    all_count = instances.count()
    user_count = instances.filter(owner=username).count()
    all_label_count = {}
    user_label_count = {}
    for label in ["U", "N", "H", "F"]:
        all_label_count[label] = instances.filter(stat=label).count()
        user_label_count[label] = instances.filter(stat=label, owner=username).count()
    all_label_month_count = []
    user_label_month_count = []
    for month in range(1, 13):
        all_label_month_count.append(instances.filter(created_date__month=month).count())
        user_label_month_count.append(instances.filter(created_date__month=month, owner=username).count())

    return_data = {
        "all_count": all_count,
        "user_count": user_count,
        "all_label_count": all_label_count,
        "user_label_count": user_label_count,
        "all_label_month_count": all_label_month_count,
        "user_label_month_count": user_label_month_count,
    }
    json_data = json.dumps(return_data)
    return HttpResponse(json_data, content_type='application/json')