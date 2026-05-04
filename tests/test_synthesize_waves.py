"""Tests for tools/synthesize_waves.py CLI behavior."""
import synthesize_waves


def test_jobs_greater_than_one_is_rejected(capsys):
    rc = synthesize_waves.main(["--list", "--jobs", "2"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "currently runs serially" in captured.err
