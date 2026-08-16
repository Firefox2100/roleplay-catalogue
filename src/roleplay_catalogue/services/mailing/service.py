from email.message import EmailMessage

from aiosmtplib import SMTP
from jinja2 import Environment


class MailingService:
    def __init__(self,
                 client: SMTP,
                 sender: str,
                 template_environment: Environment,
                 ):
        self._client = client
        self._sender = sender
        self._templates = template_environment

    def render_template(self,
                        template_name: str,
                        **context,
                        ) -> str:
        return self._templates.get_template(template_name).render(**context)

    async def send_email(self,
                         recipients: str | list[str],
                         subject: str,
                         text_body: str,
                         html_body: str | None = None,
                         ) -> None:
        recipient_list = [recipients] if isinstance(recipients, str) else recipients
        message = EmailMessage()
        message['From'] = self._sender
        message['To'] = ', '.join(recipient_list)
        message['Subject'] = subject
        message.set_content(text_body)

        if html_body:
            message.add_alternative(html_body, subtype='html')

        await self._client.send_message(message)
