from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QLabel, QApplication


class Toast(QLabel):
    """پیام کوتاه گوشهٔ صفحه — ۱.۵ ثانیه می‌ماند، ۰.۳ ثانیه محو می‌شود.
    برای پیام‌های موفقیت/کوچک؛ مودال فقط برای خطا و تأیید."""

    @staticmethod
    def show(text: str, kind: str = "ok"):
        colors = {
            "ok": ("#16a34a", "#ffffff"),
            "info": ("#1d4ed8", "#ffffff"),
            "warn": ("#d97706", "#241300"),
        }
        bg, fg = colors.get(kind, colors["ok"])
        box = QLabel(text)
        box.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {fg}; border-radius: 10px;"
            f" padding: 10px 22px; font-weight: bold;"
            f" border: 1px solid rgba(255,255,255,0.25); }}")
        box.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        box.setAttribute(Qt.WA_TransparentForMouseEvents)
        box.adjustSize()
        scr = QApplication.primaryScreen().availableGeometry()
        box.move(scr.right() - box.width() - 24, scr.top() + 24)
        box.setWindowOpacity(1.0)
        box.show()
        anim = QPropertyAnimation(box, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        box._anim = anim  # نگه‌داشتن ارجاع تا زباله‌روب حذفش نکند
        QTimer.singleShot(1500, anim.start)
        QTimer.singleShot(1900, box.close)
        QTimer.singleShot(1950, box.deleteLater)