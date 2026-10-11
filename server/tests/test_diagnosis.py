from app.services.diagnosis import diagnose


def test_undeclared_identifier():
    md = diagnose("error: use of undeclared identifier 'cout'", "ce")
    assert md is not None
    assert "标识符未声明" in md


def test_undefined_reference():
    md = diagnose("undefined reference to `foo()'", "ce")
    assert md is not None
    assert "链接错误" in md


def test_segfault_runtime():
    md = diagnose("Segmentation fault (core dumped)", "re")
    assert md is not None
    assert "段错误" in md


def test_no_hit_returns_none():
    assert diagnose("some totally unknown error xyz", "ce") is None
    assert diagnose(None, "ce") is None


def test_missing_semicolon():
    md = diagnose("error: expected ';' before 'return'", "ce")
    assert md is not None
    assert "分号" in md
