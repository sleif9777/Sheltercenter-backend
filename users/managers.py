import random
import string
from django.contrib.auth.base_user import BaseUserManager

from .enums import SecurityLevels

class UserProfileManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, primary_email, password=None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not primary_email:
            raise ValueError("The Email must be set")
        if not password:
            password = (''.join(
                random.choice(
                    string.ascii_uppercase + 
                    string.ascii_lowercase + 
                    string.digits
                ) for _ in range(8)
            ))
        primary_email = self.normalize_email(primary_email)
        user = self.model(primary_email=primary_email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, primary_email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("security_level", SecurityLevels.SUPERUSER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(primary_email, password, **extra_fields)