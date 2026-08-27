from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    ORGANIZER = 'organizer', 'Organizer'
    ATTENDEE = 'attendee', 'Attendee'


class OrganizerApprovalStatus(models.TextChoices):
    NOT_REQUIRED = 'not_required', 'Not required'
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    DENIED = 'denied', 'Denied'


class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Users must have a username.')

        email = self.normalize_email(email) if email else None
        role = extra_fields.pop('role', UserRole.ATTENDEE)

        if role == UserRole.ADMIN and not extra_fields.get('is_staff'):
            raise ValueError('Admin role can only be assigned to staff users.')

        if 'organizer_status' not in extra_fields:
            extra_fields['organizer_status'] = (
                OrganizerApprovalStatus.APPROVED
                if role == UserRole.ORGANIZER
                else OrganizerApprovalStatus.NOT_REQUIRED
            )

        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault(
            'organizer_status',
            OrganizerApprovalStatus.NOT_REQUIRED,
        )

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.ATTENDEE,
    )

    email_verified = models.BooleanField(default=False)

    organizer_status = models.CharField(
        max_length=20,
        choices=OrganizerApprovalStatus.choices,
        default=OrganizerApprovalStatus.NOT_REQUIRED,
    )

    # Firebase Cloud Messaging token for push notifications
    fcm_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="FCM Token"
    )

    objects = UserManager()

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_organizer(self):
        return self.role == UserRole.ORGANIZER

    @property
    def is_attendee(self):
        return self.role == UserRole.ATTENDEE

    @property
    def is_pending_organizer(self):
        return (
            self.is_organizer
            and self.organizer_status == OrganizerApprovalStatus.PENDING
        )

    @property
    def is_denied_organizer(self):
        return (
            self.is_organizer
            and self.organizer_status == OrganizerApprovalStatus.DENIED
        )

    @property
    def is_approved_organizer(self):
        return (
            self.is_organizer
            and self.organizer_status == OrganizerApprovalStatus.APPROVED
        )

    @property
    def can_publish_events(self):
        return self.is_admin or self.is_approved_organizer

    def clean(self):
        super().clean()
        if self.role == UserRole.ADMIN and not self.is_staff:
            raise ValidationError({'role': 'Admin role requires staff privileges.'})
        if self.is_superuser and self.role != UserRole.ADMIN:
            raise ValidationError({'role': 'Superusers must have the Admin role.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
