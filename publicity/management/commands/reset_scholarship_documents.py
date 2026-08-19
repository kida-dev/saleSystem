from django.core.management.base import BaseCommand
from django.db import transaction

from publicity.models import (
    ScholarshipRequestDocument,
    DocumentNumberSequence,
)


class Command(BaseCommand):

    help = (
        "奨学生募集依頼文書のテストデータを初期化します。"
        "中学校・生徒・教員データは削除しません。"
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--keep-sequence",
            action="store_true",
            help=(
                "DocumentNumberSequenceを残します。"
                "文書履歴だけ削除したい場合に使用します。"
            ),
        )

        parser.add_argument(
            "--yes",
            action="store_true",
            help="確認を省略して実行します。",
        )

    def handle(
        self,
        *args,
        **options,
    ):

        document_count = (
            ScholarshipRequestDocument.objects.count()
        )

        sequence_count = (
            DocumentNumberSequence.objects.count()
        )

        keep_sequence = options[
            "keep_sequence"
        ]

        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "========================================"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "奨学生募集依頼文書データを初期化します"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "========================================"
            )
        )

        self.stdout.write(
            f"文書履歴：{document_count}件"
        )

        if keep_sequence:
            self.stdout.write(
                "文書番号管理：削除しません"
            )
        else:
            self.stdout.write(
                f"文書番号管理：{sequence_count}件"
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "以下のデータは削除されません。"
            )
        )

        self.stdout.write("・募集対象生徒")
        self.stdout.write("・中学校情報")
        self.stdout.write("・教員")
        self.stdout.write("・部活動")

        self.stdout.write("")

        # ========================================
        # 確認
        # ========================================

        if not options["yes"]:

            answer = input(
                "本当に削除しますか？ "
                "yes と入力してください: "
            )

            if answer.lower() != "yes":

                self.stdout.write(
                    self.style.WARNING(
                        "処理を中止しました。"
                    )
                )

                return

        # ========================================
        # 削除処理
        #
        # corrected_from が PROTECT のため、
        # 「自分を訂正元として参照している文書がない」
        # 末端レコードから順に削除する
        # ========================================

        deleted_document_count = 0

        with transaction.atomic():

            while (
                ScholarshipRequestDocument.objects.exists()
            ):

                leaf_documents = (
                    ScholarshipRequestDocument.objects
                    .filter(
                        corrected_documents__isnull=True
                    )
                    .distinct()
                )

                leaf_count = (
                    leaf_documents.count()
                )

                if leaf_count == 0:

                    raise RuntimeError(
                        "訂正文書の参照関係を"
                        "解決できませんでした。"
                    )

                leaf_documents.delete()

                deleted_document_count += (
                    leaf_count
                )

            # ====================================
            # 文書番号管理
            # ====================================

            if not keep_sequence:

                (
                    DocumentNumberSequence.objects
                    .all()
                    .delete()
                )

        # ========================================
        # 完了
        # ========================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "初期化が完了しました。"
            )
        )

        self.stdout.write(
            f"削除した文書履歴："
            f"{deleted_document_count}件"
        )

        if keep_sequence:

            self.stdout.write(
                "文書番号管理は保持しました。"
            )

        else:

            self.stdout.write(
                f"文書番号管理："
                f"{sequence_count}件を削除しました。"
            )