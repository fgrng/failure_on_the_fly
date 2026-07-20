# Von Django 6.0.7 am 20.07.2026 um 10:07 erzeugt.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Ergänzt den Entstehungszeitpunkt einer Erhebungsbindung."""

    dependencies = [
        ("erhebungen", "0007_merge_issue_83_issue_84"),
    ]

    operations = [
        migrations.AddField(
            model_name="erhebungsbindung",
            name="erstellt_am",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
