from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('murojaatlar', '0002_demo_users'),
    ]

    operations = [
        # UserProfile ga telegram_id qo'shish
        migrations.AddField(
            model_name='userprofile',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True, verbose_name='Telegram ID'),
        ),
        # Eski priority qiymatlarini yangilash (4,5 → 3 ga)
        migrations.RunSQL(
            sql="UPDATE murojaatlar_murojaat SET priority = 3 WHERE priority > 3;",
            reverse_sql="",
        ),
        # Eski muhtojlik turlarini yangilash
        migrations.RunSQL(
            sql="UPDATE murojaatlar_murojaat SET muhtojlik_turi = 'boshqa' WHERE muhtojlik_turi IN ('ijara','toy','taziya');",
            reverse_sql="",
        ),
    ]
