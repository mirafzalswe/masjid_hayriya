from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_demo_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('murojaatlar', 'UserProfile')

    users = [
        {
            'username': 'admin',
            'password': 'admin',
            'first_name': 'Admin',
            'last_name': 'Administrator',
            'is_superuser': True,
            'is_staff': True,
            'role': 'admin',
        },
        {
            'username': 'hodim',
            'password': 'hodim',
            'first_name': 'Masjid',
            'last_name': 'Hodim',
            'is_superuser': False,
            'is_staff': False,
            'role': 'imam',
        },
        {
            'username': 'viewer',
            'password': 'viewer',
            'first_name': 'Viewer',
            'last_name': 'Foydalanuvchi',
            'is_superuser': False,
            'is_staff': False,
            'role': 'hodim',
        },
    ]

    for u in users:
        user, created = User.objects.get_or_create(username=u['username'])
        user.first_name = u['first_name']
        user.last_name = u['last_name']
        user.is_superuser = u['is_superuser']
        user.is_staff = u['is_staff']
        user.is_active = True
        user.password = make_password(u['password'])
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={'role': u['role']}
        )


def reverse_demo_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    for username in ['admin', 'hodim', 'viewer']:
        User.objects.filter(username=username).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('murojaatlar', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_demo_users, reverse_demo_users),
    ]
