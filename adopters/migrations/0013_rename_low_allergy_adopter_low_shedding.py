from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("adopters", "0012_alter_adopter_gender_preference_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="adopter",
            old_name="low_allergy",
            new_name="low_shedding",
        ),
    ]
