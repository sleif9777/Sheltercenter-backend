from enum import Enum

from django.db import models


class SecurityLevel(models.IntegerChoices, Enum):
    ADOPTER = 0
    GREETER = 1
    ADMIN = (2,)
    SUPERUSER = (3,)


class ImportFileTypes(models.IntegerChoices, Enum):
    CSV = (
        1,
        "text/csv",
    )
    EXCEL = 2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class FormContexts(models.IntegerChoices, Enum):
    NEW = 1, "Upload"
    EDIT = 2, "Edit"
