# src/gui/dialogs/point_dialog.py
# Диалог для ввода и редактирования характерной точки границы земельного участка.
# Позволяет задать номер точки, координаты X и Y, среднюю квадратическую погрешность (СКП),
# а также префикс номера и описание закрепления (опционально).

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt

from ...models import CharacteristicPoint
from ...utils.logger import get_logger

logger = get_logger(__name__)


class PointDialog(QDialog):
    """
    Диалог редактирования характерной точки.
    Позволяет просматривать и изменять атрибуты точки:
    - порядковый номер точки (обязательное целое положительное число)
    - координата X (обязательное вещественное число)
    - координата Y (обязательное вещественное число)
    - средняя квадратическая погрешность (СКП) – опционально, вещественное число
    - префикс номера точки (опционально, строка, например "н" для новых точек)
    - описание закрепления точки (опционально, строка)
    """

    def __init__(self, parent, point: CharacteristicPoint = None):
        """
        Инициализация диалога.

        Args:
            parent: Родительский виджет.
            point: Существующий объект CharacteristicPoint для редактирования.
                   Если None, создаётся новый объект (но в этом диалоге новый не создаётся,
                   он передаётся извне).
        """
        super().__init__(parent)
        self.point = point  # точка, которую редактируем (обязательно должна быть передана)
        self.setWindowTitle("Редактирование характерной точки")
        self.setModal(True)
        self.resize(400, 250)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Создание интерфейса диалога."""
        layout = QFormLayout(self)

        # Номер точки (целое число)
        self.num_spin = QDoubleSpinBox()  # используем DoubleSpinBox, но ограничим целыми
        self.num_spin.setDecimals(0)
        self.num_spin.setMinimum(1)
        self.num_spin.setMaximum(999999)
        self.num_spin.setSingleStep(1)
        self.num_spin.setToolTip("Порядковый номер точки в пределах участка/контура")
        layout.addRow("Номер точки:", self.num_spin)

        # Координата X
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setDecimals(2)
        self.x_spin.setMinimum(-1e9)
        self.x_spin.setMaximum(1e9)
        self.x_spin.setSingleStep(0.1)
        self.x_spin.setToolTip("Координата X в метрах (с точностью до 0.01 м)")
        layout.addRow("X (м):", self.x_spin)

        # Координата Y
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setDecimals(2)
        self.y_spin.setMinimum(-1e9)
        self.y_spin.setMaximum(1e9)
        self.y_spin.setSingleStep(0.1)
        self.y_spin.setToolTip("Координата Y в метрах (с точностью до 0.01 м)")
        layout.addRow("Y (м):", self.y_spin)

        # Средняя квадратическая погрешность (СКП)
        self.delta_spin = QDoubleSpinBox()
        self.delta_spin.setDecimals(2)
        self.delta_spin.setMinimum(0.0)
        self.delta_spin.setMaximum(100.0)
        self.delta_spin.setSingleStep(0.01)
        self.delta_spin.setToolTip("Средняя квадратическая погрешность положения точки (в метрах)")
        self.delta_spin.setSpecialValueText("не указана")  # текст при значении 0
        # Устанавливаем значение по умолчанию для новых точек
        if self.point and self.point.id is None:
            self.delta_spin.setValue(0.1)
        layout.addRow("СКП (м):", self.delta_spin)

        # Префикс номера точки (необязательное текстовое поле)
        self.pref_edit = QLineEdit()
        self.pref_edit.setMaxLength(30)
        self.pref_edit.setPlaceholderText("например, 'н' для новых точек")
        self.pref_edit.setToolTip("Префикс номера точки (необязательно)")
        layout.addRow("Префикс:", self.pref_edit)

        # Описание закрепления точки (необязательное поле)
        self.desc_edit = QLineEdit()
        self.desc_edit.setMaxLength(120)
        self.desc_edit.setPlaceholderText("описание геодезического знака и т.п.")
        self.desc_edit.setToolTip("Описание закрепления точки на местности")
        layout.addRow("Закрепление:", self.desc_edit)

        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_data(self):
        """Заполнение полей данными из self.point."""
        if self.point:
            self.num_spin.setValue(self.point.point_number)
            self.x_spin.setValue(self.point.x)
            self.y_spin.setValue(self.point.y)
            self.delta_spin.setValue(self.point.delta if self.point.delta is not None else 0.0)
            self.pref_edit.setText(self.point.point_pref or "")
            self.desc_edit.setText(self.point.description or "")

    def validate_and_accept(self):
        """
        Проверка корректности введённых данных и закрытие диалога.
        """
        # Номер точки должен быть целым положительным (уже обеспечено спинбоксом)
        point_number = int(self.num_spin.value())

        # Координаты могут быть любыми числами – дополнительных проверок не требуется,
        # так как спинбоксы уже ограничивают диапазон.

        # СКП – если 0, считаем что не указано
        delta = self.delta_spin.value() if self.delta_spin.value() > 0 else None

        # Префикс и описание – строки, могут быть пустыми
        pref = self.pref_edit.text().strip() or None
        desc = self.desc_edit.text().strip() or None

        # Записываем значения в объект точки
        self.point.point_number = point_number
        self.point.x = self.x_spin.value()
        self.point.y = self.y_spin.value()
        self.point.delta = delta
        self.point.point_pref = pref
        self.point.description = desc

        logger.debug(f"Точка {point_number} отредактирована: X={self.point.x}, Y={self.point.y}")
        self.accept()