Eventify

Eventify is a Django-based event management platform that allows users to interact with events according to their roles.

The project is being developed as a community project, with different contributors working on separate Git branches.

Current Project

The current development work includes the user account and authentication system.

The system supports three main user roles:

Admin — manages the platform.

Organizer — creates and manages events.

Attendee — participates in events.

Technologies Used

Python

Django 6.0.7

Django REST Framework

Pillow

PyMySQL

Python Decouple

SQLite/MySQL depending on the development configuration

Project Structure

Project-B-Eventify/

│

├── authentication/       # Authentication and user account functionality

├── Eventify/             # Main Django application/project configuration

├── eventPlatform/        # Project configuration

├── templates/            # HTML templates

├── [manage.py]([http://manage.py](http://manage.py))             # Django management script

├── requirements.txt      # Python dependencies

├── env.example           # Example environment variables

├── .gitignore            # Files excluded from Git

└── [README.md]([http://README.md](http://README.md))             # Project documentation