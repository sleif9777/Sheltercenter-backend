import ssl
import traceback
from django.conf import settings
from django.core.mail import send_mail, get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from smtplib import SMTP

from environment_settings.enums import EnvironmentType
from environment_settings.models import EnvironmentSettings

class EmailService():
    content_html = ""
    content_plain = ""
    message = EmailMultiAlternatives()

    def __init__(self, title, template_path, context, recipients, attachments=[]):
        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type not in [EnvironmentType.PRODUCTION, EnvironmentType.STAGING]:
            recipients = [environment.test_recipient_email]

        if environment.environment_type == EnvironmentType.PRODUCTION:
            title = "[TEST EMAIL] " + title

        self.content_html = render_to_string(
            'email_templates/{0}.html'.format(template_path), context)
        self.message.subject = title
        self.message.from_email = environment.default_sending_email
        self.message.to = recipients
        self.body = self.plain_content()
        self.message.attach_alternative(self.content_html, "text/html")

        for attachment in attachments:
            self.message.attach_file(attachment)

    def send(self, always_send=False):
        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type == EnvironmentType.STAGING and not always_send:
            return

        try:
            if "office365" in settings.EMAIL_HOST:
                with SMTP(settings.EMAIL_HOST, 587, timeout=100) as server:
                    context = ssl.create_default_context()
                    login_email = settings.EMAIL_HOST_USER
                    password = settings.EMAIL_HOST_PASSWORD
                    print(login_email, password)
                    
                    server.connect()
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(login_email, password)

                    self.message.send()
                    server.quit()
            else:
                self.message.send()
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise(e)

    def plain_content(self):
        return strip_tags(self.content_html)