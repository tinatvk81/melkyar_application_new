import sys

from PySide6.QtWidgets import QApplication

from ui.styles import apply_persian_rtl_style
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from updater import check_for_update


def main():
    app = QApplication(sys.argv)
    apply_persian_rtl_style(app)

    window_holder = {}

    def show_main_window():
        window_holder["login"].close()
        window_holder["main"] = MainWindow()
        window_holder["main"].show()
        check_for_update(window_holder["main"])

    login_window = LoginWindow(on_success=show_main_window)
    window_holder["login"] = login_window
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
