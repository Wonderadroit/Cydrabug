from cydra.runtime import detect_runtime


def test_runtime_report_detects_supported_proot_ubuntu_environment(monkeypatch):
    monkeypatch.setattr("cydra.runtime.platform.system", lambda: "Linux")
    monkeypatch.setattr("cydra.runtime.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("cydra.runtime.platform.release", lambda: "6.17.0-PRoot-Distro")

    def fake_run(argv, timeout=10):
        values = {
            ("proot", "--version"): (True, "proot 5.1.0"),
            ("python", "--version"): (True, "Python 3.13.13"),
            ("git", "--version"): (True, "git version 2.51.0"),
        }
        return values.get(tuple(argv), (False, None))

    monkeypatch.setattr("cydra.runtime._run", fake_run)
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: type("F", (), {"read": lambda self: "ID=ubuntu\n"})())
    report = detect_runtime()
    assert report.profile == "proot-ubuntu"
    assert report.ready
    assert report.architecture == "aarch64"


def test_runtime_report_detects_android_kernel_with_ubuntu_userspace(monkeypatch):
    monkeypatch.setattr("cydra.runtime.platform.system", lambda: "Android")
    monkeypatch.setattr("cydra.runtime.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("cydra.runtime.platform.release", lambda: "6.17.0-PRoot-Distro")
    monkeypatch.setattr("cydra.runtime._run", lambda argv, timeout=10: (True, "ok"))
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: type("F", (), {"read": lambda self: "ID=ubuntu\n"})())
    report = detect_runtime()
    assert report.profile == "proot-ubuntu"
    assert report.ready
    assert report.platform == "android"


def test_runtime_report_accepts_python3_when_python_alias_is_missing(monkeypatch):
    monkeypatch.setattr("cydra.runtime.platform.system", lambda: "Linux")
    monkeypatch.setattr("cydra.runtime.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("cydra.runtime.platform.release", lambda: "6.17.0-PRoot-Distro")

    def fake_run(argv, timeout=10):
        values = {
            ("proot", "--version"): (True, "proot 5.1.0"),
            ("python", "--version"): (False, None),
            ("python3", "--version"): (True, "Python 3.12.3"),
            ("git", "--version"): (True, "git version 2.51.0"),
        }
        return values.get(tuple(argv), (False, None))

    monkeypatch.setattr("cydra.runtime._run", fake_run)
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: type("F", (), {"read": lambda self: "ID=ubuntu\n"})())
    report = detect_runtime()
    assert report.ready
    assert report.capabilities[3].observed == "Python 3.12.3"


def test_runtime_report_is_blocked_when_required_proot_is_missing(monkeypatch):
    monkeypatch.setattr("cydra.runtime.platform.system", lambda: "Linux")
    monkeypatch.setattr("cydra.runtime.platform.machine", lambda: "aarch64")
    monkeypatch.setattr("cydra.runtime.platform.release", lambda: "6.17.0")
    monkeypatch.setattr("cydra.runtime._run", lambda argv, timeout=10: (True, "ok") if tuple(argv) != ("proot", "--version") else (False, None))
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: type("F", (), {"read": lambda self: "ID=ubuntu\n"})())
    report = detect_runtime()
    assert not report.ready
    assert "proot" in report.missing_required
