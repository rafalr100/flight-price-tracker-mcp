"""Tests for the buy/wait verdict heuristic."""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _verdict(current, history):
    from server import _verdict as v
    return v(current, history)


def test_not_enough_data():
    label, _ = _verdict(500, [500, 600, 550])
    assert "not enough data" in label.lower()


def test_buy_lowest_ever():
    history = [800, 750, 900, 820, 780, 760]
    label, _ = _verdict(700, history)
    assert "lowest" in label.lower()


def test_buy_good_deal():
    history = [900, 880, 920, 870, 910, 930, 890, 960, 850, 940]
    label, _ = _verdict(800, history)
    assert "BUY" in label


def test_wait_expensive():
    history = [500, 520, 490, 510, 530, 480, 515, 495, 505, 525]
    label, _ = _verdict(900, history)
    assert "WAIT" in label


def test_neutral():
    history = [500, 520, 490, 510, 530, 480, 515, 495, 505, 525]
    avg = sum(history) / len(history)
    label, _ = _verdict(round(avg), history)
    assert "NEUTRAL" in label
