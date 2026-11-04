"""復命書メール通知。既存の旅行命令用Gmail送信方式を再利用する。"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from documents.models import TravelPostReportNotification
from .travel_notifications import _send_with_gmail_api, PUBLIC_BASE_URL

logger = logging.getLogger(__name__)


def queue_post_report_notification(*, report, notification_type, recipient_teacher, comment=""):
    subjects = {
        "review_request": "【小林西高等学校】復命書の確認依頼",
        "returned": "【小林西高等学校】復命書の差戻し",
        "completed": "【小林西高等学校】復命書の承認完了",
    }
    if notification_type not in subjects:
        raise ValueError("不明な復命書通知種別です。")
    email = (recipient_teacher.user.email or "").strip() if recipient_teacher and recipient_teacher.user_id else ""
    name = recipient_teacher.name if recipient_teacher else ""
    record = TravelPostReportNotification.objects.create(
        report=report, notification_type=notification_type, recipient_email=email,
        recipient_name=name, subject=subjects[notification_type],
        status="queued" if email else "skipped",
        error_message="" if email else "宛先ユーザーのメールアドレスが未設定です。",
    )
    if not email:
        return record

    order = report.travel_order
    applicant = order.responsible_teacher.name
    travel_date = timezone.localtime(order.start_datetime).strftime("%Y/%m/%d")
    # 差戻しは編集画面へ、それ以外は確認画面へ。URLはCloud Run本番に統一。
    url_name = "documents:travel_post_report_edit" if notification_type == "returned" else "documents:travel_post_report_review"
    detail_url = PUBLIC_BASE_URL.rstrip("/") + reverse(url_name, kwargs={"pk": order.pk})
    intros = {
        "review_request": f"{applicant}先生の復命書が確認待ちになりました。",
        "returned": "復命書が差し戻されました。内容を修正し、再提出してください。",
        "completed": "復命書の最終承認が完了しました。",
    }
    intro = intros[notification_type]
    reason = f"\n差戻し理由：{comment}" if notification_type == "returned" and comment else ""
    body = (f"{name} 様\n\n{intro}\n\n"
            f"申請者：{applicant}\n出張日：{travel_date}\n"
            f"用務地：{order.destination_area}\n用務：{order.purpose}{reason}\n\n"
            f"確認する：{detail_url}\n\n"
            "※このメールは教務支援システムから自動送信されています。")
    reason_html = (f"<p><strong>差戻し理由：</strong><br>{escape(comment)}</p>"
                   if notification_type == "returned" and comment else "")
    html = ("<html lang='ja'><body style='font-family:sans-serif;color:#243746'>"
            "<div style='max-width:600px;margin:auto;padding:24px;border:1px solid #ddd'>"
            "<h2>小林西高等学校｜復命書</h2>"
            f"<p>{escape(name)} 様</p><p>{escape(intro)}</p>"
            f"<p>申請者：{escape(applicant)}<br>出張日：{escape(travel_date)}<br>"
            f"用務地：{escape(order.destination_area)}<br>用務：{escape(order.purpose)}</p>"
            f"{reason_html}<p><a href='{escape(detail_url)}'>復命書を確認する →</a></p>"
            "<small>※このメールは教務支援システムから自動送信されています。</small>"
            "</div></body></html>")

    def send_after_commit():
        try:
            mode = getattr(settings, "TRAVEL_NOTIFICATION_MODE", "console")
            if mode not in ("console", "gmail_api"):
                raise RuntimeError("TRAVEL_NOTIFICATION_MODE は console / gmail_api のみ対応です。")
            sender = (getattr(settings, "TRAVEL_GMAIL_SENDER", "") if mode == "gmail_api"
                      else getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.invalid"))
            if mode == "gmail_api" and not sender:
                raise RuntimeError("TRAVEL_GMAIL_SENDER が未設定です。")
            msg = EmailMultiAlternatives(subject=record.subject, body=body,
                                         from_email=sender, to=[email])
            msg.attach_alternative(html, "text/html")
            if mode == "console":
                msg.connection = get_connection(backend="django.core.mail.backends.console.EmailBackend")
                if msg.send() != 1:
                    raise RuntimeError("メール出力件数が0件でした。")
                status, sent_at = "preview", None
            else:
                _send_with_gmail_api(msg, sender=sender)
                status, sent_at = "sent", timezone.now()
            TravelPostReportNotification.objects.filter(pk=record.pk).update(
                status=status, sent_at=sent_at, error_message="")
        except Exception as exc:
            logger.exception("復命書通知に失敗しました: notification_id=%s", record.pk)
            try:
                TravelPostReportNotification.objects.filter(pk=record.pk).update(
                    status="failed", error_message=str(exc)[:2000])
            except Exception:
                logger.exception("復命書通知の失敗履歴を保存できませんでした")

    transaction.on_commit(send_after_commit)
    return record
