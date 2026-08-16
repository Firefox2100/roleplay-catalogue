from email.message import EmailMessage

from jinja2 import DictLoader, Environment, select_autoescape

from roleplay_catalogue.services import MailingService


class MemorySMTPClient:
    def __init__(self):
        self.messages: list[EmailMessage] = []

    async def send_message(self, message: EmailMessage):
        self.messages.append(message)


async def test_send_email_builds_multipart_message() -> None:
    client = MemorySMTPClient()
    service = MailingService(
        client=client,
        sender='no-reply@example.com',
        template_environment=Environment(
            loader=DictLoader({'message.html': '<p>Hello {{ name }}</p>'}),
            autoescape=select_autoescape(['html']),
        ),
    )

    html = service.render_template('message.html', name='<Alice>')
    await service.send_email(
        recipients='alice@example.com',
        subject='Hello',
        text_body='Hello Alice',
        html_body=html,
    )

    message = client.messages[0]
    assert message['From'] == 'no-reply@example.com'
    assert message['To'] == 'alice@example.com'
    assert message['Subject'] == 'Hello'
    assert '&lt;Alice&gt;' in message.get_body(preferencelist=('html',)).get_content()
