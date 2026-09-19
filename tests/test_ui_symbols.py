"""ASCII status tags / OS badges (no emoji)."""

from blacksmith.utils import ui


def test_status_symbols_are_ascii_tags():
    assert ui.SYMBOL_SUCCESS == "[OK]"
    assert ui.SYMBOL_ERROR == "[ERR]"
    assert ui.SYMBOL_WARNING == "[WARN]"
    assert ui.SYMBOL_INFO == "[INFO]"
    for value in (
        ui.SYMBOL_SUCCESS,
        ui.SYMBOL_ERROR,
        ui.SYMBOL_WARNING,
        ui.SYMBOL_INFO,
    ):
        assert value.isascii()


def test_os_badges_are_ascii_abbreviations():
    assert ui.format_os_badge("windows") == "Win"
    assert ui.format_os_badge("linux") == "Lin"
    assert ui.format_os_badge("macos") == "Mac"
    assert ui.format_os_badge("darwin") == "Mac"
    legend = ui.os_legend_text()
    assert legend.isascii()
    assert "Win" in legend and "Lin" in legend and "Mac" in legend
