from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.text import slugify

from .models import TeacherLoginEmail


User = get_user_model()


class TeacherSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    TeacherLoginEmailに登録済みのGoogleメールだけログインを許可する。
    学校用・個人用のどちらでも、同じTeacherへ紐づける。
    """

    def is_open_for_signup(self, request, sociallogin):
        email = self._get_email(sociallogin)

        if not email:
            return False

        return TeacherLoginEmail.objects.filter(
            email__iexact=email,
            is_allowed=True,
            teacher__is_active=True,
        ).exists()

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = self._get_email(sociallogin)

        login_email = (
            TeacherLoginEmail.objects
            .select_related("teacher", "teacher__user")
            .filter(
                email__iexact=email,
                is_allowed=True,
                teacher__is_active=True,
            )
            .first()
        )

        if login_email is None:
            messages.error(
                request,
                "このGoogleアカウントは利用者として登録されていません。",
            )

            raise ImmediateHttpResponse(
                redirect("publicity:login_denied")
            )

        teacher = login_email.teacher

        if teacher.user is None:
            user = self._create_teacher_user(
                teacher=teacher,
                email=email,
            )

            teacher.user = user
            teacher.save(
                update_fields=[
                    "user",
                    "updated_at",
                ]
            )

        sociallogin.connect(
            request,
            teacher.user,
        )

    def _get_email(self, sociallogin):
        email = (
            sociallogin.account.extra_data.get("email")
            or sociallogin.user.email
            or ""
        )

        return email.strip().lower()

    def _create_teacher_user(self, teacher, email):
        base_username = slugify(
            f"teacher-{teacher.employee_number}"
        )

        username = base_username
        counter = 1

        while User.objects.filter(
            username=username
        ).exists():
            username = f"{base_username}-{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=teacher.name,
        )

        user.set_unusable_password()
        user.save(
            update_fields=[
                "password",
            ]
        )

        return user