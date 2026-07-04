import pytest


@pytest.fixture(autouse=True)
def _no_real_cli(monkeypatch):
    """Never detect or shell out to a real agent CLI during tests.

    Adapters use ``shutil.which`` to detect CLI agents and Claude Code shells
    out to ``claude``; default both to absent so detection is deterministic and
    no real subprocess runs. Tests that exercise CLI behavior re-patch as needed.
    """
    monkeypatch.setattr("shutil.which", lambda name: None)


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
