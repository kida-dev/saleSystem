import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from publicity.models import Teacher


class Command(BaseCommand):
    help = "CSVファイルから教員情報を一括登録・更新します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="読み込むCSVファイルのパス",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            raise CommandError(
                f"CSVファイルが見つかりません：{csv_path}"
            )

        created_count = 0
        updated_count = 0

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            required_columns = {
                "employee_number",
                "position",
                "name",
                "assignment",
                "subject",
                "responsibility",
                "club",
                "is_active",
            }

            actual_columns = set(reader.fieldnames or [])

            missing_columns = required_columns - actual_columns

            if missing_columns:
                raise CommandError(
                    "CSVに必要な列がありません："
                    + ", ".join(sorted(missing_columns))
                )

            for row_number, row in enumerate(reader, start=2):
                try:
                    employee_number = int(
                        row["employee_number"].strip()
                    )

                    name = row["name"].strip()

                    if not name:
                        raise ValueError("氏名が空欄です。")

                    is_active_text = (
                        row.get("is_active", "")
                        .strip()
                        .lower()
                    )

                    is_active = is_active_text in {
                        "true",
                        "1",
                        "yes",
                        "有効",
                    }

                    teacher, created = Teacher.objects.update_or_create(
                        employee_number=employee_number,
                        defaults={
                            "position": row["position"].strip(),
                            "name": name,
                            "assignment": row["assignment"].strip(),
                            "subject": row["subject"].strip(),
                            "responsibility": row[
                                "responsibility"
                            ].strip(),
                            "club": row["club"].strip(),
                            "is_active": is_active,
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as error:
                    raise CommandError(
                        f"{row_number}行目の処理に失敗しました："
                        f"{error}"
                    ) from error

        self.stdout.write(
            self.style.SUCCESS(
                "教員一括登録が完了しました。"
                f" 新規：{created_count}件"
                f" 更新：{updated_count}件"
            )
        )