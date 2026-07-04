import pytest


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    # os.path.expanduser on POSIX honors $HOME; ensure no cached override
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return home
