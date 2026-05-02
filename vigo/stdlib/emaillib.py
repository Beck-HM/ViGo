"""ViGo Email Library - SMTP Email Sending"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class EmailSender:
    def __init__(self):
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587
        self.username = None
        self.password = None

    def configure(self, host, port, username, password):
        self.smtp_host = host
        self.smtp_port = int(port)
        self.username = username
        self.password = password
        return True

    def send(self, to, subject, body, from_addr=None):
        if not self.username:
            raise ViGoError("Email not configured. Use email_configure() first.")

        msg = MIMEMultipart()
        msg["From"] = from_addr or self.username
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(str(body), "plain", "utf-8"))

        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            return "Email sent successfully."
        except Exception as e:
            raise ViGoError(f"Email send failed: {e}")


_email = EmailSender()


def register(env):
    env.define('email_configure', BuiltinFunction(
        lambda host, port, user, pwd: _email.configure(host, port, user, pwd),
        'email_configure'))
    env.define('email_send', BuiltinFunction(
        lambda to, subject, body, from_addr=None: _email.send(to, subject, body, from_addr),
        'email_send'))