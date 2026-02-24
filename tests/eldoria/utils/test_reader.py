
import pytest

from eldoria.exceptions.general import LogFileNotFound
from eldoria.utils.reader import tail_lines


def test_tail_lines_returns_last_n_lines(tmp_path):
    log_file = tmp_path / "test.log"

    content = "\n".join([f"ligne {i}" for i in range(10)])
    log_file.write_text(content, encoding="utf-8")

    result = tail_lines(path=str(log_file), maxlen=3)

    assert result == "ligne 7\nligne 8\nligne 9"


def test_tail_lines_returns_all_if_less_than_maxlen(tmp_path):
    log_file = tmp_path / "test.log"

    content = "a\nb\nc"
    log_file.write_text(content, encoding="utf-8")

    result = tail_lines(path=str(log_file), maxlen=10)

    assert result == content


def test_tail_lines_handles_utf8(tmp_path):
    log_file = tmp_path / "test.log"

    content = "é\nà\nç\n🚀"
    log_file.write_text(content, encoding="utf-8")

    result = tail_lines(path=str(log_file), maxlen=2)

    assert result == "ç\n🚀"


def test_tail_lines_raises_if_file_not_found(tmp_path):
    missing_file = tmp_path / "missing.log"

    with pytest.raises(LogFileNotFound):
        tail_lines(path=str(missing_file), maxlen=5)


def test_tail_lines_default_maxlen(tmp_path):
    log_file = tmp_path / "test.log"

    content = "\n".join(str(i) for i in range(300))
    log_file.write_text(content, encoding="utf-8")

    result = tail_lines(path=str(log_file))  # maxlen par défaut = 200

    lines = result.splitlines()
    assert len(lines) == 200
    assert lines[0] == "100"
    assert lines[-1] == "299"