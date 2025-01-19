from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from posixpath import basename
import smtplib
import ssl
import traceback
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from smtplib import SMTP

from environment_settings.enums import EnvironmentType
from environment_settings.models import EnvironmentSettings

class EmailService():
    content_html = ""
    content_plain = ""
    subject = ""
    sender = ""
    recipient = ""
    attachments = []
    # message = MIMEMultipart()

    def __init__(self, title, template_path, context, recipients, attachments=[]):
        self.content_html = render_to_string(
            'email_templates/{0}.html'.format(template_path), context)
        self.content_html.encode("utf-8")
        self.content_plain = self.plain_content()
        self.subject = title
        self.sender = "savinggracencscheduler@gmail.com"
        self.attachments = attachments

        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type not in [EnvironmentType.PRODUCTION, EnvironmentType.STAGING]:
            self.recipient = environment.test_recipient_email
        else:
            self.recipient = recipients

        if environment.environment_type != EnvironmentType.PRODUCTION:
            self.subject = "[TEST EMAIL] " + title
        
    def create_message(self):
        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type not in [EnvironmentType.PRODUCTION, EnvironmentType.STAGING]:
            self.sender = "leifersam9@gmail.com"
        
        message = MIMEMultipart()
        message['Subject'] = self.subject
        message['From'] = self.sender
        message['To'] = self.recipient
        message['reply-to'] = 'adoptions@savinggracenc.org'
        
        html = MIMEText(self.content_html, 'html')

        if len(self.attachments) > 0:
            for attachment in self.attachments:
                with open(attachment, "rb") as a:
                    part = MIMEApplication(
                        a.read(),
                        Name=basename(attachment)
                    )
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(attachment)
                message.attach(part)

        message.attach(html)

        return message

    def connect_to_gmail(self, message):
        context = ssl.create_default_context()
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=100)
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.send_message(message)
        server.quit()
        self.message = None

    def send(self, always_send=False, cc_adoptions=True):
        environment = EnvironmentSettings.objects.get(pk=1)
        message = self.create_message()

        if environment.environment_type == EnvironmentType.STAGING:
            if not always_send:
                return

        if cc_adoptions:
            message['Cc'] = 'adoptions@savinggracenc.org'

        try:
            self.connect_to_gmail(message)
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise(e)

    def plain_content(self):
        return strip_tags(self.content_html)