from django.db import models


class JuniorHighSchool(models.Model):
    number = models.IntegerField("No", null=True, blank=True)
    name = models.CharField("学校名", max_length=100)
    city = models.CharField("市町村", max_length=50, blank=True)
    principal_name = models.CharField("校長名", max_length=50, blank=True)
    tel = models.CharField("電話番号", max_length=30, blank=True)
    address = models.CharField("住所", max_length=255, blank=True)
    third_grade_total = models.IntegerField("3年合計", default=0)

    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "中学校情報"
        verbose_name_plural = "中学校情報"
        ordering = ["number", "id"]

    def __str__(self):
        return self.name


class JuniorHighClass(models.Model):
    school = models.ForeignKey(
        JuniorHighSchool,
        on_delete=models.CASCADE,
        related_name="classes",
        verbose_name="中学校"
    )
    class_name = models.CharField("クラス名", max_length=50)
    boys = models.IntegerField("男子", default=0)
    girls = models.IntegerField("女子", default=0)
    total = models.IntegerField("計", default=0)

    class Meta:
        verbose_name = "中学校クラス人数"
        verbose_name_plural = "中学校クラス人数"
        ordering = ["school__number", "id"]

    def __str__(self):
        return f"{self.school.name} {self.class_name}"