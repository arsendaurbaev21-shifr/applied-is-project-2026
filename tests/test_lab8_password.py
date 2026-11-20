"""No SQL dependency: exercise the real primary Cargo password validator."""
import pytest
from backend.schema import password
from backend.errors import AppError


@pytest.mark.parametrize('value',['','123456789','password123','1111111111'])
def test_weak_password_rejected(value):
    with pytest.raises(AppError): password(value)


def test_long_passphrase_accepted():
    value='Cargo learning example 2026!'
    assert password(value)==value
