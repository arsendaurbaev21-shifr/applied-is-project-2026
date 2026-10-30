from pathlib import Path
from unittest.mock import Mock,patch
import pytest
from backend.install import backup_and_drop,run_script


@pytest.mark.parametrize('name',['master','model','msdb','tempdb','OtherDatabase','QazCargo;DROP DATABASE master'])
def test_reset_rejects_other_names(name):
    conn=Mock()
    with pytest.raises(ValueError):backup_and_drop(conn,name,name)
    conn.cursor.assert_not_called()


def test_reset_requires_exact_confirmation():
    conn=Mock()
    with pytest.raises(ValueError):backup_and_drop(conn,'QazCargo','yes')
    conn.cursor.assert_not_called()


@pytest.mark.parametrize('failure',['BACKUP','VERIFYONLY'])
def test_failed_backup_never_drops_and_restores_multiuser(failure):
    conn=Mock();cur=conn.cursor.return_value;cur.nextset.return_value=False
    with patch('backend.install.backup',side_effect=RuntimeError(failure)):
        with pytest.raises(RuntimeError):backup_and_drop(conn,'QazCargo','QazCargo')
    statements=[c.args[0] for c in cur.execute.call_args_list]
    assert not any('DROP DATABASE' in s for s in statements)
    assert any('MULTI_USER' in s for s in statements)


def test_script_stops_at_first_failed_batch(tmp_path):
    path=tmp_path/'script.sql';path.write_text('SELECT 1;\nGO\nBROKEN;\nGO\nSELECT 3;')
    conn=Mock();cur=conn.cursor.return_value;cur.nextset.return_value=False
    cur.execute.side_effect=[None,RuntimeError('failed')]
    with pytest.raises(RuntimeError):run_script(conn,path)
    assert cur.execute.call_count==2
