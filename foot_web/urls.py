from django.contrib import admin
from django.urls import path
from footapp.views import get_collection_by_id, add_collection, patch_collection, get_collection, auth
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('get_collection/',csrf_exempt(get_collection),name="get_collection"),
    path("get_collection/<int:id>", csrf_exempt(get_collection_by_id), name = "get_collection_by_id"),
    path('add_collection',csrf_exempt(add_collection),name="add_collection"),
    path('auth',csrf_exempt(auth),name="auth"),
    path('patch_collection',csrf_exempt(patch_collection),name="patch_collection"),

    # path('upload_file/',csrf_exempt(upload_file),name="upload_file"),

]
