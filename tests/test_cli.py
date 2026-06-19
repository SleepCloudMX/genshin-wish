"""Tests for CLI commands."""
import json
from click.testing import CliRunner
from genshin_wish.cli.main import main


def test_char_basic():
    runner = CliRunner()
    result = runner.invoke(main, ["char", "--n-up", "7", "--quantile", "0.5"])
    assert result.exit_code == 0
    assert "期望抽数" in result.output
    assert "637" in result.output or "638" in result.output


def test_char_json():
    runner = CliRunner()
    result = runner.invoke(main, ["char", "--n-up", "2", "--pulls", "200", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "expected" in data
    assert "probability" in data
    assert data["expected"] > 0


def test_weapon():
    runner = CliRunner()
    result = runner.invoke(main, ["weapon", "--count-a", "1", "--pulls", "200"])
    assert result.exit_code == 0
    assert "期望抽数" in result.output


def test_std():
    runner = CliRunner()
    result = runner.invoke(main, ["std", "--n-gold", "5", "--pulls", "371"])
    assert result.exit_code == 0
    assert "期望抽数" in result.output


def test_joint():
    runner = CliRunner()
    result = runner.invoke(main, ["joint", "--char-up", "2", "--weapon-count", "1", "--pulls", "500"])
    assert result.exit_code == 0
    assert "期望抽数" in result.output


def test_char_method_consistency():
    """dp-path and dp-state give identical results."""
    runner = CliRunner()
    r1 = runner.invoke(main, ["char", "--n-up", "7", "--pulls", "800", "--format", "json"])
    r2 = runner.invoke(main, ["char", "--n-up", "7", "--pulls", "800", "--method", "dp-state", "--format", "json"])
    assert r1.exit_code == 0
    assert r2.exit_code == 0
    d1 = json.loads(r1.output)
    d2 = json.loads(r2.output)
    from pytest import approx
    assert d1["expected"] == approx(d2["expected"])


def test_char_method_dp_path_limit():
    """dp-path rejects n_up > 20."""
    runner = CliRunner()
    result = runner.invoke(main, ["char", "--n-up", "21", "--method", "dp-path"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "dp-path" in str(result.exception)


def test_char_method_clt():
    """clt method works for large n_up."""
    runner = CliRunner()
    result = runner.invoke(main, ["char", "--n-up", "501", "--method", "clt", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["expected"] > 0
