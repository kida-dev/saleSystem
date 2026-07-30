from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


ROLE_CLUB_ADVISOR = "club_advisor"
ROLE_PUBLICITY_ADMIN = "publicity_admin"
ROLE_SYSTEM_ADMIN = "system_admin"


def get_active_teacher(user):
    """
    ログインユーザーに紐づく、有効なTeacherを返す。

    Djangoスーパーユーザーの場合はTeacher未紐づけでも許可判定できるため、
    Noneを返す。
    """
    if not user.is_authenticated:
        return None

    try:
        teacher = user.publicity_teacher
    except AttributeError:
        return None
    except user.publicity_teacher.RelatedObjectDoesNotExist:
        return None

    if not teacher.is_active:
        return None

    return teacher


def active_teacher_required(view_func):
    """
    有効な教員、またはDjangoスーパーユーザーだけ許可する。
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        teacher = get_active_teacher(request.user)

        if teacher is None:
            raise PermissionDenied(
                "このアカウントは、利用可能な教員として登録されていません。"
            )

        request.teacher = teacher

        return view_func(request, *args, **kwargs)

    return wrapped_view


def club_advisor_required(view_func):
    """
    部活動顧問以上の権限を許可する。

    現在の3段階では、利用可能な全ロールを対象とする。
    将来「閲覧のみ」を追加した場合に、ここで除外する。
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        teacher = get_active_teacher(request.user)

        if teacher is None:
            raise PermissionDenied(
                "この機能を利用できる教員情報がありません。"
            )

        allowed_roles = {
            ROLE_CLUB_ADVISOR,
            ROLE_PUBLICITY_ADMIN,
            ROLE_SYSTEM_ADMIN,
        }

        if teacher.role not in allowed_roles:
            raise PermissionDenied(
                "中学校・中学生情報を登録する権限がありません。"
            )

        request.teacher = teacher

        return view_func(request, *args, **kwargs)

    return wrapped_view


def publicity_admin_required(view_func):
    """
    広報管理者またはシステム管理者だけ許可する。
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        teacher = get_active_teacher(request.user)

        if teacher is None:
            raise PermissionDenied(
                "この機能を利用できる教員情報がありません。"
            )

        allowed_roles = {
            ROLE_PUBLICITY_ADMIN,
            ROLE_SYSTEM_ADMIN,
        }

        if teacher.role not in allowed_roles:
            raise PermissionDenied(
                "広報管理者以上の権限が必要です。"
            )

        request.teacher = teacher

        return view_func(request, *args, **kwargs)

    return wrapped_view


def system_admin_required(view_func):
    """
    システム管理者またはDjangoスーパーユーザーだけ許可する。
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        teacher = get_active_teacher(request.user)

        if teacher is None:
            raise PermissionDenied(
                "この機能を利用できる教員情報がありません。"
            )

        if teacher.role != ROLE_SYSTEM_ADMIN:
            raise PermissionDenied(
                "システム管理者の権限が必要です。"
            )

        request.teacher = teacher

        return view_func(request, *args, **kwargs)

    return wrapped_view