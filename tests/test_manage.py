from unittest.mock import Mock,patch
from backend import manage


def test_admin_retries_invalid_email_and_password_without_writing_early(capsys):
    database=Mock()
    database.one.return_value=None
    with patch('backend.manage.transaction') as transaction, patch('builtins.input',side_effect=['missing-at.example.com','admin@example.com','Test Admin']), patch('backend.manage.getpass',side_effect=['short','first-valid-password','does-not-match','final-valid-password','final-valid-password']), patch('backend.manage.generate_password_hash',return_value='test-hash') as hash_password:
        transaction.return_value.__enter__.return_value=database
        manage.admin_console()
    transaction.assert_called_once_with(True)
    hash_password.assert_called_once_with('final-valid-password',method='scrypt')
    database.insert.assert_called_once()
    values=database.insert.call_args.args[2]
    assert values['Email']=='admin@example.com'
    assert values['PasswordHash']=='test-hash'
    output=capsys.readouterr().out
    assert '@' in output and 'сәйкес келмейді' in output
    assert 'first-valid-password' not in output and 'final-valid-password' not in output


def test_cancelled_console_has_no_traceback(capsys):
    with patch('sys.argv',['manage','admin']),patch('backend.manage.prepare_env'),patch('backend.manage.admin_console',side_effect=EOFError):
        assert manage.main()==130
    assert 'Traceback' not in capsys.readouterr().out
