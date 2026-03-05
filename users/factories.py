import csv
import email
import email.utils
import io
import traceback

import pandas
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from mimetypes import guess_type
from typing import TypedDict

from adopters.models import Adopter
from adopters.enums import ApprovalStatus
from email_templates.views import EmailViewSet

from .enums import *
from .models import UserProfile


class UploadResultsHash(TypedDict):
    successes: int
    updates: str
    failures: str
    aversions: list[str]


class UserFactory:
    def clean_records(self, adopter: Adopter, user: UserProfile):
        for record in [adopter, user]:
            if record is not None:
                record.delete()

    def send_approval_email(self, adopter: Adopter):
        if not adopter.should_send_approval_email:
            return

        EmailViewSet().ApplicationApproved(adopter)


class UserSpreadsheetFactory(UserFactory):
    rows = None

    def __init__(self, file: UploadedFile):
        file_type = self.get_file_type(file.name)

        match file_type:
            case ImportFileTypes.CSV:
                decoded_file = file.read().decode("utf-8")
                io_string = io.StringIO(decoded_file)
                all_rows = list(csv.reader(io_string, delimiter=","))
                self.rows = all_rows[1:]
            case ImportFileTypes.EXCEL:
                decoded_file = pandas.read_excel(file)
                decoded_file = decoded_file.fillna("")
                all_rows = decoded_file.values.tolist()
                self.rows = all_rows

        assert len(self.rows) > 0

    def get_file_type(self, file_name) -> ImportFileTypes:
        mime_type, _ = guess_type(file_name) or (None, None)
        
        # Check MIME type
        if mime_type == "text/csv":
            return ImportFileTypes.CSV
        elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return ImportFileTypes.EXCEL
        
        # Fallback to extension
        extension = file_name.split(".")[-1].lower()
        match extension:
            case "csv":
                return ImportFileTypes.CSV
            case "xlsx":
                return ImportFileTypes.EXCEL
            case _:
                raise ValueError(f"Unsupported file type: {file_name}")

    def run_import_batch(self) -> UploadResultsHash:
        successes, updates, failures = 0, 0, 0
        aversions = []

        for i in range(len(self.rows)):
            try:
                if not self.validate_single_row(i):
                    failures += 1
                    continue
                    
                user, created, approval_averted = self.process_single_row(i)
                
                # Skip if user is None (foster app or error)
                if user is None:
                    failures += 1
                    continue
                
                # Update batch counts
                if created:
                    successes += 1
                elif approval_averted:
                    averted_adopter = {
                        "ID": user.adopter_profile.id,
                        "name": user.full_name,
                    }
                    aversions.append(averted_adopter)
                else:
                    updates += 1
                    
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                traceback.print_exc()
                failures += 1

        aversions = list({a["ID"]: a for a in aversions}.values())

        return {
            "successes": successes,
            "updates": updates,
            "failures": failures,
            "aversions": aversions,
        }
        
    def validate_single_row(self, index):
        row_data = self.rows[index]
        validate_length = [27, 14, 15, 4]

        for i in validate_length:
            value = row_data[i]
            if pandas.isna(value) or len(str(value).strip()) < 1:
                print(f"Row {index} failed validation at index {i}: {value}")
                return False

        email_value = row_data[27]
        parsed = email.utils.parseaddr(email_value)[1]
        print(f"Row {index} email validation: {email_value} -> {parsed}")
        
        if parsed == "":
            print(f"Row {index} email validation FAILED")
            return False
        
        return True

    def process_single_row(self, index) -> tuple[UserProfile, bool, bool]:
        row_data = self.rows[index]

        if self.is_foster_application(row_data[1]):
            return None, False, False

        new_status, approval_averted = Adopter.get_application_status(row_data[4], row_data[27])
        adopter: Adopter = None
        user: UserProfile = None

        try:
            adopter, adopter_created = self.create_new_adopter(index, new_status)
            user, user_created = self.create_new_user(index, adopter)

            self.send_approval_email(adopter)

            adopter.update_last_upload()

            return user, (adopter_created and user_created), approval_averted
        except:
            if not adopter or not user: # if either is missing, since you need both
                self.clean_records(adopter, user)
            return None, False, False

    def is_foster_application(self, app_type: str):
        return "Foster" in app_type

    def create_new_adopter(self, index: int, new_status: ApprovalStatus) -> tuple[Adopter, bool]:
        row_data = self.rows[index]

        adopter, adopter_created = Adopter.objects.update_or_create(
            primary_email=row_data[27].lower(),
            defaults={
                "status": new_status,
                "shelterluv_id": row_data[13],
                "shelterluv_app_id": row_data[0],
                "approved_until": Adopter.get_default_approval_date(),
                "application_comments": row_data[12],
            },
            create_defaults={
                "status": new_status,
                "shelterluv_id": row_data[13],
                "shelterluv_app_id": row_data[0],
                "approved_until": Adopter.get_default_approval_date(),
                "application_comments": row_data[12],
            },
        )

        return adopter, adopter_created

    def create_new_user(self, index: int, adopter: Adopter) -> tuple[UserProfile, bool]:
        row_data = self.rows[index]

        user, user_created = UserProfile.objects.update_or_create(
            primary_email=row_data[27].lower(),
            defaults={
                "adopter_profile": adopter,
                "first_name": row_data[14].title(),
                "last_name": row_data[15].title(),
                "street_address": row_data[17].title(),
                "city": row_data[19].title(),
                "state": row_data[20].upper(),
                "postal_code": row_data[22],
                "phone_number": row_data[23],
                "secondary_email": row_data[28],
                "archived": False,
            },
            create_defaults={
                "adopter_profile": adopter,
                "first_name": row_data[14].title().strip(),
                "last_name": row_data[15].title().strip(),
                "password": None,
                "street_address": row_data[17].title().strip(),
                "city": row_data[19].title().strip(),
                "state": row_data[20].upper().strip(),
                "postal_code": row_data[22],
                "phone_number": row_data[23],
                "secondary_email": row_data[28],
                "security_level": SecurityLevel.ADOPTER,
            },
        )

        if user_created:
            user.set_unusable_password()
            user.save()

        return user, user_created
    

class UserFormFactory(UserFactory):
    context: FormContexts
    form_data: dict

    @property
    def is_edit_context(self):
        return self.context == FormContexts.EDIT

    @property
    def is_new_context(self):
        return self.context == FormContexts.NEW

    def __init__(self, validated_data: dict):
        self.context = validated_data.get("context", FormContexts.NEW)
        self.form_data = validated_data

    def process_form_data(self) -> tuple[Adopter, bool, bool]:
        if self.is_new_context:
            new_status, approval_averted = Adopter.get_application_status(
                self.form_data["status"], self.form_data["primaryEmail"]
            )
        else:
            current_status = Adopter.objects.get(primary_email=self.form_data["primaryEmail"]).status
            new_status, approval_averted = self.form_data["status"], False
            newly_approved = new_status == ApprovalStatus.APPROVED and (current_status != new_status)

        adopter: Adopter
        user: UserProfile

        try:
            adopter, adopter_created = self.create_new_adopter(new_status)
            user, user_created = self.create_new_user(adopter)

            if self.is_new_context or newly_approved:
                self.send_approval_email(adopter)
            return adopter, (adopter_created and user_created), approval_averted
        except Exception as e:
            traceback.print_exc()
            traceback.print_stack()
            # TODO email Sam
            self.clean_records(adopter, user)
            return None, False, False

    def create_new_adopter(self, new_status: ApprovalStatus) -> tuple[Adopter, bool]:
        adopter, adopter_created = Adopter.objects.update_or_create(
            primary_email=self.form_data["primaryEmail"].lower(),
            defaults={"status": new_status, "internal_notes": self.form_data["internalNotes"]},
            create_defaults={
                "approved_until": Adopter.get_default_approval_date(),
                "status": self.form_data["status"],
                "internal_notes": self.form_data["internalNotes"],
            },
        )

        return adopter, adopter_created

    def create_new_user(self, adopter: Adopter):
        self.form_data
        user, user_created = UserProfile.objects.update_or_create(
            primary_email=self.form_data["primaryEmail"].lower(),
            defaults={
                "first_name": self.form_data["firstName"].title(),
                "last_name": self.form_data["lastName"].title(),
                "archived": False,
            },
            create_defaults={
                "adopter_profile": adopter,
                "first_name": self.form_data["firstName"].title(),
                "last_name": self.form_data["lastName"].title(),
                "security_level": SecurityLevel.ADOPTER,
            },
        )

        return user, user_created
