from django.shortcuts import render
from django.views.generic import View
from footapp.models import Database
from django.core import serializers
from django.http import JsonResponse
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


_path = Path(__file__, '..').resolve()
# Create your views here.

"""
Diagram
Login user : same time
Time line: when should they finish labelling for us
Hosting : which platform

DINO : Finetune with freeze itself and add extra layers

Croos entrophy: classification
Triplet loss: k-nn Vectorspace

Maybe create anothor collection_log
"""

USER = {
    'admin' : 'admin123'
}

'''
TODO:

    IMPORTANT: JSONWebToken(cookie) for user in every request 
        if no cookie found --> send 401 (unauthorize)

    1) API --> GET Handle start/end index and filter (use parameter) --> add new GET API [get_collection]
        1.1) Filter:
            - label (stat)
            - side
        1.2) Search 
            - name
        1.3) Sort [by what & ascending\descending]
            - create at
            - id
            - name

    2) API --> PATCH (F_name: patch_collection)
        body can get one or more of the following:
            - stat
            - size
            - remark
            - deleted

    3) API --> POST (F_name: auth)
        body:
            - username
            - password
'''

# NOY FINISED
@login_required
def get_collection(request): #1)
    SORT_OPTION = ['created_date', 'pk', 'name']
    FILTER_BY = [None, 'stat', 'side']
    FILTERS_SIDE = [None, 'L', 'R']
    FILTERS_STAT = [None, 'N', 'H', 'F', 'U']

    filter_by = request.GET.get('filter_by', None)
    filter = request.GET.get('filter', None)
    search = request.GET.get('search', None)
    sort = request.GET.get('sort', 'pk')
    ascending = request.GET.get('ascending', True)

    try:
        start = int(request.GET.get('start'))
        end = int(request.GET.get('end'))
    except:
        return HttpResponseBadRequest()

    if filter_by not in FILTER_BY or sort not in SORT_OPTION or (filter_by == 'stat' and filter not in FILTERS_STAT) or (filter_by == 'side' and filter not in FILTERS_SIDE):
        return HttpResponseBadRequest()
    
    if not ascending:
        sort = '-'+sort

    if request.method=='GET':
        instances = Database.objects.all()
        if filter_by:
            if filter_by == 'stat':
                try:
                    filtered_instances = instances.filter(stat = filter).order_by(sort)[start-1:end-1]
                except:
                    filtered_instances = instances.filter(stat = filter).order_by(sort)[start-1:]
            if filter_by == 'side':
                try:
                    filtered_instances = instances.filter(side = filter).order_by(sort)[start-1:end-1]
                except:
                    filtered_instances = instances.filter(side = filter).order_by(sort)[start-1:]
            data = serializers.serialize('json', filtered_instances)
            return HttpResponse(data, content_type='application/json')
        elif search:
            try:
                search_instances = instances.filter(name__icontains = search).order_by(sort)[start-1:end-1]
            except:
                search_instances = instances.filter(name__icontains = search).order_by(sort)[start-1]
            data = serializers.serialize('json', search_instances)
            return HttpResponse(data, content_type='application/json')
        else:
            try:
                sorted_instances = instances.order_by(sort)[start-1:end-1]
            except:
                sorted_instances = instances.order_by(sort)[start-1:]
            data = serializers.serialize('json', sorted_instances)
            return HttpResponse(data, content_type='application/json')

@login_required
def get_collection_by_id(request, id): 
    instance = Database.objects.filter(id = id)
    data = serializers.serialize('json', instance)
    return HttpResponse(data, content_type='application/json')

@login_required
def add_collection(request):
    if request.method=='POST':
        received_json_data= json.loads(request.body)
        try:
            Database.objects.create(**received_json_data)
            # Database.save()
            return HttpResponse('POST successfully!!')
        except Exception:
            return HttpResponse('POST successful BUT DID NOT PUT IN DATABASE!!')

    return HttpResponse('We got request')

@login_required
def patch_collection(request):#2)
    if request.method=='PATCH':
        try:
            received_json_data= json.loads(request.body)
            Database.objects.filter(id = received_json_data['id']).update(
                name = received_json_data['name'],
                stat = received_json_data['stat'],
                side = received_json_data['side'],
                remark = received_json_data['remark'],
                deleted = received_json_data['deleted'],
                modify_date = timezone.now()
            )
            if received_json_data['deleted'] == True:
                Database.objects.filter(id = received_json_data['id']).update(deleted_date = timezone.now())    
            return HttpResponse('Patch successfully!')
        except:
            return HttpResponseBadRequest()

def auth(request):#3)
    if request.method=='POST':
        received_json_data= json.loads(request.body)
        username = received_json_data['username']
        password = received_json_data['password']
        print(username)
        print(password)
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            return HttpResponse('Login successfully!')
        else:
            return HttpResponseForbidden()
        
@login_required
def logout_api(request):
    logout(request)
    return HttpResponse('Logout successfully!')


@login_required
def upload_file(request):
    received_json_data= json.loads(request.body)
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    _path = os.path.dirname(__file__)
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(_path+'\\credential.json', scope)
    drive = GoogleDrive(gauth)
    file_name = received_json_data['file_name']+'.jpg'
    _file = drive.CreateFile({'parents':[{'id':'1IYdmr-oWqKKCjq-RsjBbS9kEgcnY_G4R'}],'title':f'{file_name}', 'mimeType':'image/jpeg'})
    img_data = received_json_data['img_file']
    with open(_path+'\\temp.jpg', "wb") as fh:
        fh.write(base64.b64decode(img_data))
        fh.close()
    _file.SetContentFile(_path+'\\temp.jpg')
    _file.Upload()
    Database.objects.filter(name = received_json_data['file_name']).update(link = str(_file['id']))
    return HttpResponse('Uploaded to GDrive!')

@login_required
def get_img(request, id:int):
    instance = Database.objects.filter(id = id)
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    _path = os.path.dirname(__file__)
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(_path+'\\credential.json', scope)
    drive = GoogleDrive(gauth)
    file_id = instance[0].__dict__['link']
    _file = drive.CreateFile({'id':f'{file_id}', 'mimeType':'image/jpeg'})
    _file.GetContentFile(filename=_path+'\\temp.jpg', mimetype='image/jpeg')
    with open(_path+'\\temp.jpg', "rb") as f:
        encoded_image = base64.b64encode(f.read())
        return HttpResponse(encoded_image)