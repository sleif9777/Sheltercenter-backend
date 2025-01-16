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
    message = MIMEMultipart()

    def __init__(self, title, template_path, context, recipients, attachments=[]):
        environment = EnvironmentSettings.objects.get(pk=1)

        if environment.environment_type not in [EnvironmentType.PRODUCTION, EnvironmentType.STAGING]:
            recipients = environment.test_recipient_email

        if environment.environment_type != EnvironmentType.PRODUCTION:
            title = "[TEST EMAIL] " + title
        
        self.content_html = render_to_string(
            'email_templates/{0}.html'.format(template_path), context)
        self.content_html.encode("utf-8")
        self.content_plain = self.plain_content()
        self.message['Subject'] = title
        self.message['From'] = "savinggracencscheduler@gmail.com"
        self.message['To'] = recipients
        self.message['reply-to'] = 'adoptions@savinggracenc.org'
        
        html = MIMEText(self.content_html, 'html')
        plain = MIMEText(self.content_plain, 'text')

        if len(attachments) > 0:
            for attachment in attachments:
                with open(attachment, "rb") as a:
                    part = MIMEApplication(
                        a.read(),
                        Name=basename(attachment)
                    )
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(attachment)
                self.message.attach(part)

        self.message.attach(html)
        # self.message.attach(plain)

    def connect_to_gmail(self):
        # if is_cc_adoptions or self.message['reply-to'] != 'sheltercenterdev@gmail.com':
        #     self.message['reply-to'], self.message['To'] = self.message['To'], self.message['reply-to']
        print(self.message.get('To'))

        context = ssl.create_default_context()
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=100)
        server.ehlo()
        server.starttls(context=context)
        # server.ehlo()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.send_message(self.message)
        server.quit()
        print("SUCCEED")

    def send(self, always_send=False, cc_adoptions=True):
        environment = EnvironmentSettings.objects.get(pk=1)

        # print(self.message['To'])

        if environment.environment_type == EnvironmentType.STAGING:
            if not always_send:
                return

        if cc_adoptions:
            print("HIT")
            self.message['Cc'] = 'adoptions@savinggracenc.org'

        try:
            # context = ssl.create_default_context()
            # server = smtplib.SMTP('smtp.gmail.com', 587, timeout=100)
            # server.ehlo()
            # server.starttls(context=context)
            # server.ehlo()
            # server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            # server.send_message(self.message)
            # server.quit()
            self.connect_to_gmail()
            # self.connect_to_gmail(is_cc_adoptions=True)
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise(e)

    def plain_content(self):
        return strip_tags(self.content_html)