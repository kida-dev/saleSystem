from django.contrib import admin
from django.urls import include, path

from publicity import views


urlpatterns = [
    # Django管理画面
    path(
        "admin/",
        admin.site.urls,
    ),

    # django-allauth
    # Googleログイン・ログアウト・コールバック
    path(
        "accounts/",
        include("allauth.urls"),
    ),

    # saleSystemトップ
    path(
        "",
        views.top,
        name="top",
    ),

    # 広報支援機能
    path(
        "publicity/",
        include("publicity.urls"),
    ),
]