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

        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username, email, password)
            action = 'Created'
        else:
            user.email = email
            user.role = 'admin'
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            action = 'Updated'

        self.stdout.write(
            self.style.SUCCESS(
                f'{action} admin user "{username}". '
                f'Log in at /login/ — admin dashboard is at /admin/.'
            )
        )
