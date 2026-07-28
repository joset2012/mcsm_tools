import os

from mcsm_tools import system_check


def test_find_7z_prefers_path_lookup(monkeypatch, tmp_path):
    seven_zip = tmp_path / "7z"
    seven_zip.write_text("", encoding="utf-8")
    monkeypatch.setattr(system_check, "SYSTEM", "Linux")
    monkeypatch.setattr(system_check.shutil, "which", lambda name: str(seven_zip) if name == "7z" else None)

    assert system_check._find_7z() == os.path.abspath(str(seven_zip))


def test_find_7z_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr(system_check, "SYSTEM", "Linux")
    monkeypatch.setattr(system_check.shutil, "which", lambda name: None)
    monkeypatch.setattr(system_check.os.path, "exists", lambda path: False)

    assert system_check._find_7z() is None


def test_find_7z_checks_windows_install_dirs(monkeypatch, tmp_path):
    installed = tmp_path / "7-Zip" / "7z.exe"
    installed.parent.mkdir(parents=True)
    installed.write_text("", encoding="utf-8")
    monkeypatch.setattr(system_check, "SYSTEM", "Windows")
    monkeypatch.setattr(system_check.shutil, "which", lambda name: None)
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "x86"))

    assert system_check._find_7z() == str(installed)


def test_ensure_font_installed_copies_ttf_files(monkeypatch, tmp_path):
    fonts_src = tmp_path / "fonts"
    fonts_src.mkdir()
    (fonts_src / "Mono-Regular.ttf").write_text("font", encoding="utf-8")
    (fonts_src / "notes.txt").write_text("ignore me", encoding="utf-8")
    home = tmp_path / "home"

    monkeypatch.setattr(system_check, "_FONTS_DIR", str(fonts_src))
    monkeypatch.setattr(system_check, "SYSTEM", "Linux")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(system_check.subprocess, "run", lambda *a, **k: None)

    assert system_check.ensure_font_installed() is True
    installed = home / ".fonts"
    assert (installed / "Mono-Regular.ttf").exists()
    assert not (installed / "notes.txt").exists()


def test_ensure_font_installed_without_bundled_fonts(monkeypatch, tmp_path):
    monkeypatch.setattr(system_check, "_FONTS_DIR", str(tmp_path / "missing"))
    assert system_check.ensure_font_installed() is False


def test_ensure_font_installed_requires_localappdata_on_windows(monkeypatch, tmp_path):
    fonts_src = tmp_path / "fonts"
    fonts_src.mkdir()
    monkeypatch.setattr(system_check, "_FONTS_DIR", str(fonts_src))
    monkeypatch.setattr(system_check, "SYSTEM", "Windows")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert system_check.ensure_font_installed() is False


def test_run_reports_environment(monkeypatch, capsys):
    monkeypatch.setattr(system_check, "SEVEN_ZIP_PATH", None)
    monkeypatch.setattr(system_check, "_find_7z", lambda: "/usr/bin/7z")
    monkeypatch.setattr(system_check, "ensure_font_installed", lambda: True)

    system_check.run()

    err = capsys.readouterr().err
    assert "7-Zip: /usr/bin/7z" in err
    assert system_check.SEVEN_ZIP_PATH == "/usr/bin/7z"


def test_run_warns_when_7z_missing_and_font_install_fails(monkeypatch, capsys):
    monkeypatch.setattr(system_check, "SEVEN_ZIP_PATH", None)
    monkeypatch.setattr(system_check, "_find_7z", lambda: None)

    def boom():
        raise RuntimeError("no fontconfig")

    monkeypatch.setattr(system_check, "ensure_font_installed", boom)

    system_check.run()

    err = capsys.readouterr().err
    assert "7-Zip 未安装" in err
    assert "字体安装异常: no fontconfig" in err
