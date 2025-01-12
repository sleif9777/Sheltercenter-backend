from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from environment_settings.enums import EnvironmentType
from environment_settings.models import EnvironmentSettings

class EmailService():
    content_html = ""
    content_plain = ""
    message = EmailMultiAlternatives()

    def __init__(self, title, template_path, context, recipients, attachments=[]):
        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type != EnvironmentType.PRODUCTION:
            recipients = [environment.test_recipient_email]

        self.content_html = render_to_string(
            'email_templates/{0}.html'.format(template_path), context)
        self.message.subject = title
        self.message.from_email = environment.default_sending_email
        self.message.to = recipients
        self.body = self.plain_content()
        self.message.attach_alternative(self.content_html, "text/html")

        for attachment in attachments:
            self.message.attach_file(attachment)

    def send(self):
        self.message.send()

    def plain_content(self):
        return strip_tags(self.content_html)