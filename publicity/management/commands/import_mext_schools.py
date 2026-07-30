import csv
import re
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from publicity.models import JuniorHighSchool


class Command(BaseCommand):
    help = (
        "文部科学省の学校コードCSVから、"
        "現存する中学校の情報を取り込みます。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="文部科学省CSVファイルのパス",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "DBへ保存せず、"
                "取込件数だけ確認します。"
            ),
        )

        parser.add_argument(
            "--prefecture",
            type=str,
            default="",
            help=(
                "指定した都道府県だけ取り込みます。"
                "例：宮崎県"
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        csv_path = Path(
            options["csv_path"]
        )

        dry_run = options["dry_run"]

        target_prefecture = (
            options["prefecture"]
            .strip()
        )

        if not csv_path.exists():
            raise CommandError(
                f"CSVファイルが見つかりません："
                f"{csv_path}"
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        try:
            csv_file = csv_path.open(
                mode="r",
                encoding="cp932",
                newline="",
            )

        except UnicodeDecodeError as exc:
            raise CommandError(
                "CSVをCP932で読み込めませんでした。"
            ) from exc

        with csv_file:
            reader = csv.reader(
                csv_file
            )

            try:
                # 1行目：文部科学省 学校コード一覧
                next(reader)

                # 2行目：列名
                raw_headers = next(reader)

            except StopIteration as exc:
                raise CommandError(
                    "CSVに必要な行がありません。"
                ) from exc

            headers = [
                self.normalize_header(header)
                for header in raw_headers
            ]

            for row_number, row in enumerate(
                reader,
                start=3,
            ):
                if not row:
                    continue

                # 列数不足を補完
                if len(row) < len(headers):
                    row.extend(
                        [""] * (
                            len(headers)
                            - len(row)
                        )
                    )

                data = dict(
                    zip(
                        headers,
                        row,
                    )
                )

                try:
                    result = self.process_row(
                        data=data,
                        dry_run=dry_run,
                        target_prefecture=(
                            target_prefecture
                        ),
                    )

                except Exception as exc:
                    error_count += 1

                    self.stderr.write(
                        self.style.ERROR(
                            f"{row_number}行目："
                            f"{exc}"
                        )
                    )

                    continue

                if result == "created":
                    created_count += 1

                elif result == "updated":
                    updated_count += 1

                else:
                    skipped_count += 1

        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "ドライランのため、"
                    "DBには保存していません。"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "取込処理が完了しました。"
            )
        )

        self.stdout.write(
            f"新規登録：{created_count}件"
        )

        self.stdout.write(
            f"更新：{updated_count}件"
        )

        self.stdout.write(
            f"対象外：{skipped_count}件"
        )

        self.stdout.write(
            f"エラー：{error_count}件"
        )

    @transaction.atomic
    def process_row(
        self,
        data,
        dry_run,
        target_prefecture,
    ):
        school_code = (
            data
            .get("学校コード", "")
            .strip()
        )

        school_type = (
            data
            .get("学校種", "")
            .strip()
        )

        prefecture_raw = (
            data
            .get("都道府県番号", "")
            .strip()
        )

        establishment_type = (
            data
            .get("設置区分", "")
            .strip()
        )

        main_branch = (
            data
            .get("本分校", "")
            .strip()
        )

        school_name = (
            data
            .get("学校名", "")
            .strip()
        )

        official_address = (
            data
            .get("学校所在地", "")
            .strip()
        )

        postal_code = (
            data
            .get("郵便番号", "")
            .strip()
        )

        abolished_date = (
            data
            .get(
                "属性情報廃止年月日",
                "",
            )
            .strip()
        )

        # 今回は通常の中学校のみ
        if not school_type.startswith(
            "C1"
        ):
            return "skipped"

        # 本校だけを対象
        if not main_branch.startswith(
            "1"
        ):
            return "skipped"

        # 廃止済みの学校は対象外
        if abolished_date:
            return "skipped"

        if not school_code:
            return "skipped"

        if not school_name:
            return "skipped"

        prefecture = (
            self.extract_prefecture(
                prefecture_raw
            )
        )

        if (
            target_prefecture
            and prefecture
            != target_prefecture
        ):
            return "skipped"

        formatted_postal_code = (
            self.format_postal_code(
                postal_code
            )
        )

        defaults = {
            "name": school_name,
            "prefecture": prefecture,
            "school_type": school_type,
            "establishment_type": (
                establishment_type
            ),
            "official_postal_code": (
                formatted_postal_code
            ),
            "official_address": (
                official_address
            ),
            "is_from_mext": True,
            "is_active": True,
        }

        existing_school = (
            JuniorHighSchool.objects
            .filter(
                school_code=school_code
            )
            .first()
        )

        if existing_school:
            if dry_run:
                return "updated"

            for field_name, value in (
                defaults.items()
            ):
                setattr(
                    existing_school,
                    field_name,
                    value,
                )

            # 本校で入力済みの住所は上書きしない
            if not existing_school.address:
                existing_school.address = official_address

            # 市町村が空欄なら、公式住所から補完
            if not existing_school.city:
                existing_school.city = self.extract_city(
                    prefecture,
                    official_address,
                )
            existing_school.save()

            return "updated"

        # 既存の手入力学校と
        # 学校名が完全一致する場合は紐付ける
        name_matches = (
            JuniorHighSchool.objects
            .filter(
                name=school_name,
                school_code__isnull=True,
            )
        )

        if name_matches.count() == 1:
            school = name_matches.first()

            if dry_run:
                return "updated"

            school.school_code = (
                school_code
            )

            for field_name, value in (
                defaults.items()
            ):
                setattr(
                    school,
                    field_name,
                    value,
                )

            if not school.address:
                school.address = (
                    official_address
                )

            school.save()

            return "updated"

        if dry_run:
            return "created"

        JuniorHighSchool.objects.create(
            number=None,
            name=school_name,
            city=self.extract_city(
                prefecture,
                official_address,
            ),
            principal_name="",
            tel="",
            address=official_address,
            third_grade_total=0,
            school_code=school_code,
            prefecture=prefecture,
            school_type=school_type,
            establishment_type=(
                establishment_type
            ),
            official_postal_code=(
                formatted_postal_code
            ),
            official_address=(
                official_address
            ),
            is_from_mext=True,
            is_active=True,
        )

        return "created"

    @staticmethod
    def normalize_header(header):
        return (
            header
            .replace("\n", "")
            .replace("\r", "")
            .replace(" ", "")
            .strip()
        )

    @staticmethod
    def format_postal_code(
        postal_code,
    ):
        digits = re.sub(
            r"\D",
            "",
            postal_code,
        )

        if len(digits) == 7:
            return (
                f"{digits[:3]}-"
                f"{digits[3:]}"
            )

        return postal_code

    @staticmethod
    def extract_prefecture(
        prefecture_raw,
    ):
        match = re.search(
            r"\((.+?)\)",
            prefecture_raw,
        )

        if not match:
            return ""

        prefecture_name = (
            match.group(1).strip()
        )

        if prefecture_name == "北海道":
            return "北海道"

        if prefecture_name == "東京":
            return "東京都"

        if prefecture_name == "京都":
            return "京都府"

        if prefecture_name == "大阪":
            return "大阪府"

        return (
            f"{prefecture_name}県"
        )

    @staticmethod
    def extract_city(
        prefecture,
        official_address,
    ):
        """
        住所から市区町村名を抽出する。

        例：
        宮崎県宮崎市○○ → 宮崎市
        宮崎県東諸県郡国富町○○ → 国富町
        """

        if not official_address:
            return ""

        address = official_address.strip()

        if prefecture and address.startswith(prefecture):
            address = address[len(prefecture):]

        match = re.match(
            r"^(?:.*?郡)?(.+?[市区町村])",
            address,
        )

        if match:
            return match.group(1)

        return ""