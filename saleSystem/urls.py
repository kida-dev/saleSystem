from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "accounts/",
        include("allauth.urls"),
    ),

    path(
        "",
        include("top.urls"),
    ),

    path(
        "publicity/",
        include("publicity.urls"),
    ),

    path(
        "documents/",
        include("documents.urls"),
    ),
]


# =========================================
# MEDIA FILES
# ローカル開発時のみアップロードファイルを配信
# =========================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )