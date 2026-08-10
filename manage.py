#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
<<<<<<< HEAD
    # CORRECTION ICI : Remplacement de omnistock par Eventify
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Eventify.settings')
=======
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_platform.settings')
>>>>>>> 67b8828 (Initial Eventify account system)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
