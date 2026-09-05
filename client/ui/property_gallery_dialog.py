from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QLabel
)

from api_client import api_client, ApiError
from session import handle_api_error

THUMBNAIL_SIZE = 140


class PropertyGalleryDialog(QDialog):
    def __init__(self, property_id: int, property_label: str = ""):
        super().__init__()
        self.property_id = property_id

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"گالری تصاویر — {property_label}" if property_label else "گالری تصاویر")
        self.resize(640, 520)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(10)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)

        add_btn = QPushButton("افزودن عکس...")
        add_btn.clicked.connect(self.handle_add_images)

        delete_btn = QPushButton("حذف عکس انتخاب‌شده")
        delete_btn.clicked.connect(self.handle_delete_selected)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)

        top_bar = QHBoxLayout()
        top_bar.addWidget(add_btn)
        top_bar.addWidget(delete_btn)
        top_bar.addStretch()
        top_bar.addWidget(close_btn)

        self.status_label = QLabel("در حال بارگذاری...")

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self.load_images()

    def load_images(self):
        self.list_widget.clear()
        try:
            images = api_client.list_property_images(self.property_id)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return

        self.status_label.setText(f"تعداد عکس‌ها: {len(images)}")
        for img in images:
            try:
                image_bytes = api_client.get_property_image_bytes(self.property_id, img["id"])
            except ApiError:
                continue  # اگر یک عکس خاص خطا داد، بقیه نمایش داده شوند
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes)
            pixmap = pixmap.scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            item = QListWidgetItem(QIcon(pixmap), img.get("original_filename") or "")
            item.setData(Qt.UserRole, img["id"])
            self.list_widget.addItem(item)

    def handle_add_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "انتخاب عکس (چند عکس هم‌زمان قابل انتخاب است)", "", "Images (*.jpg *.jpeg *.png *.webp)"
        )
        if not file_paths:
            return
        try:
            api_client.upload_property_images(self.property_id, file_paths)
        except ApiError as e:
            handle_api_error(self, e, "خطا در آپلود", critical=True)
            return
        self.load_images()

    def handle_delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "توجه", "ابتدا یک عکس را از گالری انتخاب کنید.")
            return
        confirm = QMessageBox.question(self, "تایید", "این عکس برای همیشه حذف شود؟")
        if confirm != QMessageBox.Yes:
            return
        image_id = item.data(Qt.UserRole)
        try:
            api_client.delete_property_image(self.property_id, image_id)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_images()
