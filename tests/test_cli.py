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
