from django.shortcuts import render

from publicity.models import Teacher


def top(request):

    teacher = None

    if request.user.is_authenticated:
        try:
            teacher = request.user.publicity_teacher
        except Teacher.DoesNotExist:
            teacher = None

    # --------------------------------------------------------
    # システム全体を利用できるか
    # --------------------------------------------------------

    can_use_system = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or (
                teacher is not None
                and teacher.is_active
            )
        )
    )

    # --------------------------------------------------------
    # 広報・募集支援を利用できるか
    # --------------------------------------------------------

    can_use_publicity = (
        request.user.is_superuser
        or (
            teacher is not None
            and teacher.is_active
        )
    )

    # --------------------------------------------------------
    # 今後ここにシステムごとの権限を追加する
    # --------------------------------------------------------

    # 例：
    #
    # can_use_circular = (
    #     request.user.is_superuser
    #     or (
    #         teacher is not None
    #         and teacher.is_active
    #     )
    # )

    context = {
        "teacher": teacher,
        "can_use_system": can_use_system,
        "can_use_publicity": can_use_publicity,
    }

    return render(
        request,
        "top/system_top.html",
        context,
    )