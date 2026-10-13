"""旅行命令の通知。console（確認用）/ Gmail API（実送信）に対応。"""

import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from documents.models import TravelNotification


logger = logging.getLogger(__name__)


# ==========================================================
# Gmail API: Cloud Runの実行IDから、鍵なしで送信専用SAに署名を委任
# ==========================================================
def _send_with_gmail_api(message, *, sender):
    """Workspaceのドメイン全体の委任で sender の Gmail から1通送信する。"""
    try:
        import google.auth
        from google.auth import iam
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError(
            "Gmail API送信には google-auth と requests が必要です。"
        ) from exc

    service_account_email = getattr(
        settings, "TRAVEL_GMAIL_SERVICE_ACCOUNT", ""
    ).strip()
    if not service_account_email:
        raise RuntimeError("TRAVEL_GMAIL_SERVICE_ACCOUNT が未設定です。")
    if not sender:
        raise RuntimeError("TRAVEL_GMAIL_SENDER が未設定です。")

    auth_request = GoogleAuthRequest()
    source_credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    source_credentials.refresh(auth_request)

    # IAM Credentials API の signBlob を使うため、JSON秘密鍵は不要。
    signer = iam.Signer(
        auth_request, source_credentials, service_account_email
    )
    delegated_credentials = service_account.Credentials(
        signer=signer,
        service_account_email=service_account_email,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        subject=sender,
    )
    delegated_credentials.refresh(auth_request)

    # Djangoが生成したMIME（テキスト＋HTML）をそのままGmail APIへ渡す。
    message.from_email = sender
    mime_message = message.message()
    encoded = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("ascii")
    payload = json.dumps({"raw": encoded}).encode("utf-8")
    request = UrlRequest(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {delegated_credentials.token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # アクセストークン等の秘密情報をログに残さない。
        raise RuntimeError(
            f"Gmail API送信に失敗しました（HTTP {exc.code}）。"
        ) from exc
    except URLError as exc:
        raise RuntimeError("Gmail APIに接続できませんでした。") from exc
    if not result.get("id"):
        raise RuntimeError("Gmail APIからメッセージIDが返されませんでした。")
    return result["id"]



# ==========================================================
# 教務支援システムの公開URL
# ==========================================================

PUBLIC_BASE_URL = (
    "https://sale-system-884085651960.asia-northeast1.run.app"
)


# ==========================================================
# 旅行命令のメール通知
# ==========================================================

def queue_travel_notification(
    *,
    travel_order,
    notification_type,
    recipient_teacher,
    detail_url=None,
    comment="",
):
    """
    旅行命令のメール通知を登録する。

    ・申請時：最初の承認者へ通知
    ・途中承認：次の承認者へ通知
    ・差戻し：申請者へ通知
    ・最終承認：申請者へ通知

    通知履歴はDBへ保存する。
    メール処理はDBコミット後に実行する。

    mode=console ならプレビュー、mode=gmail_api なら実送信。
    """

    # ------------------------------------------------------
    # ① 通知先のメールアドレス
    # ------------------------------------------------------

    email = ""

    if recipient_teacher and recipient_teacher.user_id:
        email = (
            recipient_teacher.user.email or ""
        ).strip()

    name = (
        recipient_teacher.name
        if recipient_teacher
        else ""
    )

    # ------------------------------------------------------
    # ② メール件名
    # ------------------------------------------------------

    subjects = {
        "review_request": "【小林西高等学校】旅行命令の確認依頼",
        "returned": "【小林西高等学校】旅行命令の差戻し",
        "completed": "【小林西高等学校】旅行命令の承認完了",
    }

    # ------------------------------------------------------
    # ③ 通知履歴を作成
    # ------------------------------------------------------

    record = TravelNotification.objects.create(
        travel_order=travel_order,
        notification_type=notification_type,
        recipient_email=email,
        recipient_name=name,
        subject=subjects[notification_type],
        status="queued" if email else "skipped",
        error_message=(
            ""
            if email
            else "宛先ユーザーのメールアドレスが未設定です。"
        ),
    )

    if not email:
        return record

    # ------------------------------------------------------
    # ④ 公開URLを生成
    # ------------------------------------------------------
    # ローカル環境で申請しても、
    # メールのリンク先はCloud Runの公開URLにする。
    #
    # detail_url引数は既存views.pyとの互換性のため残す。
    # 実際のメールには公開URLを使用する。
    # ------------------------------------------------------

    detail_path = reverse(
        "documents:travel_order_detail",
        kwargs={
            "pk": travel_order.pk,
        },
    )

    detail_url = (
        PUBLIC_BASE_URL.rstrip("/")
        + detail_path
    )

    # ------------------------------------------------------
    # ⑤ 旅行命令の情報
    # ------------------------------------------------------

    applicant = travel_order.responsible_teacher.name

    date = timezone.localtime(
        travel_order.start_datetime
    ).strftime("%Y/%m/%d")

    area = travel_order.destination_area

    purpose = travel_order.purpose

    # ------------------------------------------------------
    # ⑥ 通知種別ごとの本文
    # ------------------------------------------------------

    if notification_type == "review_request":

        heading = "旅行命令の確認依頼"

        intro = (
            f"{applicant}先生から旅行命令が提出されました。"
            "内容をご確認ください。"
        )

    elif notification_type == "returned":

        heading = "旅行命令が差し戻されました"

        intro = (
            "旅行命令が差し戻されました。"
            "内容を修正し、再申請してください。"
        )

    else:

        heading = "旅行命令が承認されました"

        intro = "旅行命令の校長承認が完了しました。"

    # ------------------------------------------------------
    # ⑦ 差戻し理由
    # ------------------------------------------------------

    reason = ""

    if notification_type == "returned" and comment:
        reason = f"\n差戻し理由：{comment}"

    # ------------------------------------------------------
    # ⑧ テキスト形式のメール
    # ------------------------------------------------------

    body = (
        f"{name} 様\n\n"
        f"{intro}\n\n"
        f"申請者：{applicant}\n"
        f"出張日：{date}\n"
        f"用務地：{area}\n"
        f"用務：{purpose}"
        f"{reason}\n\n"
        f"確認する：{detail_url}\n\n"
        "※このメールは教務支援システムから自動送信されています。\n"
        "※承認・差戻し操作はシステム上で行ってください。"
    )

    # ------------------------------------------------------
    # ⑨ HTML形式の差戻し理由
    # ------------------------------------------------------

    reason_html = ""

    if notification_type == "returned" and comment:

        reason_html = (
            '<p style="padding:12px;'
            'background:#fff3f3;'
            'border-left:4px solid #c0392b;">'
            "<strong>差戻し理由：</strong><br>"
            f"{escape(comment)}"
            "</p>"
        )

    # ------------------------------------------------------
    # ⑩ HTML形式のメール
    # ------------------------------------------------------

    html = f"""
    <!doctype html>
    <html lang="ja">

    <body style="
        font-family:sans-serif;
        color:#243746;
        background:#f5f8fa;
        padding:20px;
    ">

        <div style="
            max-width:600px;
            margin:auto;
            padding:24px;
            background:white;
            border:1px solid #d9e5e8;
            border-radius:8px;
        ">

            <div style="
                background:#126d72;
                color:white;
                padding:16px;
                font-size:20px;
                font-weight:bold;
            ">
                小林西高等学校｜教務支援システム
            </div>

            <h2 style="margin-top:24px;">
                {escape(heading)}
            </h2>

            <p>{escape(name)} 様</p>

            <p>{escape(intro)}</p>

            <table style="
                width:100%;
                border-collapse:collapse;
                margin-top:20px;
            ">

                <tr>
                    <th align="left">申請者</th>
                    <td>{escape(applicant)}</td>
                </tr>

                <tr>
                    <th align="left">出張日</th>
                    <td>{escape(date)}</td>
                </tr>

                <tr>
                    <th align="left">用務地</th>
                    <td>{escape(area)}</td>
                </tr>

                <tr>
                    <th align="left">用務</th>
                    <td style="white-space:pre-wrap;">
                        {escape(purpose)}
                    </td>
                </tr>

            </table>

            {reason_html}

            <p style="
                margin:32px 0;
                text-align:center;
            ">

                <a href="{escape(detail_url)}"
                   style="
                       background:#126d72;
                       color:white;
                       text-decoration:none;
                       padding:14px 30px;
                       border-radius:6px;
                       display:inline-block;
                       font-weight:bold;
                   ">
                    確認する →
                </a>

            </p>

            <p style="
                font-size:12px;
                color:#677;
                border-top:1px solid #ddd;
                padding-top:16px;
            ">
                ※このメールは教務支援システムから自動送信されています。<br>
                ※承認・差戻し操作はシステム上で行ってください。
            </p>

        </div>

    </body>
    </html>
    """

    # ------------------------------------------------------
    # ⑪ DBコミット後のメール処理
    # ------------------------------------------------------

    def send_after_commit():

        try:

            mode = getattr(settings, "TRAVEL_NOTIFICATION_MODE", "console")
            if mode not in ("console", "gmail_api"):
                raise RuntimeError(
                    "TRAVEL_NOTIFICATION_MODE は console / gmail_api のみ対応です。"
                )

            sender = (
                getattr(settings, "TRAVEL_GMAIL_SENDER", "")
                if mode == "gmail_api"
                else getattr(
                    settings, "DEFAULT_FROM_EMAIL", "no-reply@example.invalid"
                )
            )
            if mode == "gmail_api" and not sender:
                raise RuntimeError("TRAVEL_GMAIL_SENDER が未設定です。")

            msg = EmailMultiAlternatives(
                subject=record.subject,
                body=body,
                from_email=sender,
                to=[email],
            )
            msg.attach_alternative(html, "text/html")

            if mode == "console":
                msg.connection = get_connection(
                    backend="django.core.mail.backends.console.EmailBackend"
                )
                if msg.send() != 1:
                    raise RuntimeError("メール出力件数が0件でした。")
                new_status = "preview"
                sent_at = None
            else:
                _send_with_gmail_api(msg, sender=sender)
                new_status = "sent"
                sent_at = timezone.now()

            TravelNotification.objects.filter(pk=record.pk).update(
                status=new_status,
                sent_at=sent_at,
                error_message="",
            )

        except Exception as exc:

            logger.exception(
                "旅行命令通知に失敗しました: "
                "notification_id=%s",
                record.pk,
            )

            try:

                TravelNotification.objects.filter(
                    pk=record.pk
                ).update(
                    status="failed",
                    error_message=str(exc)[:2000],
                )

            except Exception:

                logger.exception(
                    "旅行命令通知の失敗履歴を"
                    "保存できませんでした"
                )

    # ------------------------------------------------------
    # ⑫ DBコミット後に実行
    # ------------------------------------------------------

    transaction.on_commit(
        send_after_commit
    )

    return record