import httpx


async def test_send_email_is_delivered_with_subject_and_both_bodies(mailpit) -> None:
    service, api_url = mailpit

    await service.send_email(
        recipients='alice@example.com',
        subject='Welcome',
        text_body='Welcome, Alice',
        html_body='<p>Welcome, <strong>Alice</strong></p>',
    )

    async with httpx.AsyncClient() as http:
        listing = (await http.get(f'{api_url}/api/v1/messages')).json()
        assert len(listing['messages']) == 1
        message_id = listing['messages'][0]['ID']
        message = (await http.get(f'{api_url}/api/v1/message/{message_id}')).json()

    assert message['Subject'] == 'Welcome'
    assert message['To'][0]['Address'] == 'alice@example.com'
    assert 'Welcome, Alice' in message['Text']
    assert '<strong>Alice</strong>' in message['HTML']


async def test_send_email_reaches_multiple_recipients(mailpit) -> None:
    service, api_url = mailpit

    await service.send_email(
        recipients=['alice@example.com', 'bob@example.com'],
        subject='Team update',
        text_body='Hello team',
    )

    async with httpx.AsyncClient() as http:
        listing = (await http.get(f'{api_url}/api/v1/messages')).json()

    assert len(listing['messages']) == 1
    addresses = {recipient['Address'] for recipient in listing['messages'][0]['To']}
    assert addresses == {'alice@example.com', 'bob@example.com'}
