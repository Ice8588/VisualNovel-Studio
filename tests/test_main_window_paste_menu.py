"""Task 6：MainWindow 檔案選單應含「貼上文字」action（接 _on_paste_text）。

需要 QT_QPA_PLATFORM=offscreen 執行。
"""


def _find_action(menu_bar, text: str):
    """遞迴搜尋 menu_bar 下符合文字的 QAction。"""
    for action in menu_bar.actions():
        sub = action.menu()
        if sub is not None:
            for a in sub.actions():
                if a.text() == text:
                    return a
    return None


def test_file_menu_has_paste_text_action(qapp):
    from src.ui.main_window import MainWindow

    w = MainWindow()
    menu_bar = w.menuBar()

    act = _find_action(menu_bar, "貼上文字")
    assert act is not None, "檔案選單應含『貼上文字』action"
    # 快捷鍵 Ctrl+Shift+V
    assert act.shortcut().toString() == "Ctrl+Shift+V"
