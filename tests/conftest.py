"""pytest 全域設定。

QtWebEngine + qfluentwidgets 協同需要：
1) `AA_ShareOpenGLContexts` 必須在 QApplication 建立前設定。
2) QWebEngineView 必須在 QApplication 之前 import。
3) QApplication 與 qfluentwidgets 的 qconfig singleton 需要同一個生命週期；
   因此 qapp fixture 採 session scope，所有測試共享同一個 app instance。
"""

import sys

import pytest
from PyQt6.QtCore import Qt, QCoreApplication

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

# 必須在 QApplication 建立前 import，以初始化 WebEngine
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402, F401
from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv or [""])
    yield app
