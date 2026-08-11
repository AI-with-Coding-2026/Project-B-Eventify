from django.core.management.base import BaseCommand

from authentication.models import User


class Command(BaseCommand):
    help = 'Create or reset the default Eventify admin account.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='Ritvik')
        parser.add_argument('--email', default='ritvik@example.com')
        parser.add_argument('--password', default='ASMR1234')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email},
        )
        user.email = email
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} admin user "{username}". '
                f'Log in at /admin/ with this account.'
            )
        )
