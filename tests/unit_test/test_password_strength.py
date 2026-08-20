import pytest
from pydantic import ValidationError

from roleplay_catalogue.misc import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, password_strength_error
from roleplay_catalogue.routers.auth import (
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    RegistrationRequest,
)


def test_a_password_meeting_every_rule_passes():
    assert password_strength_error('Str0ng!Pass') is None


def test_missing_lowercase_is_rejected():
    assert password_strength_error('STRONG1!PASS') == (
        'Password must contain at least one lowercase letter'
    )


def test_missing_uppercase_is_rejected():
    assert password_strength_error('str0ng!pass') == (
        'Password must contain at least one uppercase letter'
    )


def test_missing_digit_is_rejected():
    assert password_strength_error('Strong!Pass') == (
        'Password must contain at least one number'
    )


def test_missing_special_character_is_rejected():
    assert password_strength_error('Str0ngPass') == (
        'Password must contain at least one special character'
    )


def test_rules_are_checked_in_a_stable_order_for_a_password_missing_several():
    assert password_strength_error('short') == (
        'Password must contain at least one uppercase letter'
    )


def test_password_min_and_max_length_constants_match_the_documented_policy():
    assert PASSWORD_MIN_LENGTH == 8
    assert PASSWORD_MAX_LENGTH == 128


def test_registration_request_rejects_a_weak_password():
    with pytest.raises(ValidationError, match='special character'):
        RegistrationRequest(username='alice', email='alice@example.com', password='Weakpass1')


def test_registration_request_accepts_a_strong_password():
    request = RegistrationRequest(username='alice', email='alice@example.com', password='Str0ng!Pass')
    assert request.password == 'Str0ng!Pass'


def test_password_change_request_rejects_a_weak_new_password_but_not_the_current_one():
    # The current password authenticates the request and may predate this policy, so only
    # the new password is held to it.
    with pytest.raises(ValidationError, match='number'):
        PasswordChangeRequest(currentPassword='literally-anything', newPassword='NoDigits!')


def test_password_reset_confirm_request_rejects_a_weak_new_password():
    with pytest.raises(ValidationError, match='lowercase letter'):
        PasswordResetConfirmRequest(userId='user-id', token='reset-token', newPassword='ALLCAPS1!')
