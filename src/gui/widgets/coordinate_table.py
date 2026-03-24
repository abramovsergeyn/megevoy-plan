# src/gui/widgets/coordinate_table.py
# Виджет для редактирования таблицы координат характерных точек.
# Представляет собой расширенный QTableWidget с дополнительными методами
# для работы с точками: добавление, редактирование, удаление, проверка геометрии.
# Используется внутри диалога редактирования участка (parcel_dialog).

from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
    QMessageBox, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from ...models import CharacteristicPoint
from ...services.geometry_service import calculate_area, is_closed, is_self_intersecting
from ...utils.logger import get_logger
from ..dialogs.point_dialog import PointDialog  # правильный импорт

logger = get_logger(__name__)


class CoordinateTable(QTableWidget):
    """
    Таблица для редактирования координат характерных точек.
    Отображает колонки: №, X, Y, СКП.
    Предоставляет контекстное меню и кнопки для управления точками.
    """

    # Сигнал, испускаемый при изменении данных (добавление/удаление/редактирование)
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Настройка внешнего вида таблицы."""
        # Устанавливаем количество колонок и заголовки
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["№", "X", "Y", "СКП"])
        # Растягиваем колонки равномерно
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Разрешаем выделение строк
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        # Запрещаем редактирование ячеек напрямую (редактирование через диалог)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        # Включаем контекстное меню
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_points(self, points: List[CharacteristicPoint]):
        """
        Устанавливает список точек для отображения.

        Args:
            points: Список объектов CharacteristicPoint (должен быть упорядочен по point_number).
        """
        self.clearContents()
        self.setRowCount(len(points))
        for row, point in enumerate(points):
            self._set_row_data(row, point)
        self.dataChanged.emit()

    def _set_row_data(self, row: int, point: CharacteristicPoint):
        """Заполняет одну строку данными точки."""
        self.setItem(row, 0, QTableWidgetItem(str(point.point_number)))
        self.setItem(row, 1, QTableWidgetItem(f"{point.x:.2f}"))
        self.setItem(row, 2, QTableWidgetItem(f"{point.y:.2f}"))
        delta_str = f"{point.delta:.2f}" if point.delta is not None else ""
        self.setItem(row, 3, QTableWidgetItem(delta_str))

    def add_point(self, point: CharacteristicPoint):
        """
        Добавляет новую точку в таблицу (в конец).

        Args:
            point: Объект CharacteristicPoint.
        """
        row = self.rowCount()
        self.insertRow(row)
        self._set_row_data(row, point)
        self.dataChanged.emit()
        logger.debug(f"Точка {point.point_number} добавлена в таблицу")

    def update_point(self, row: int, point: CharacteristicPoint):
        """
        Обновляет данные существующей строки.

        Args:
            row: Номер строки.
            point: Обновлённый объект точки.
        """
        if 0 <= row < self.rowCount():
            self._set_row_data(row, point)
            self.dataChanged.emit()
            logger.debug(f"Точка {point.point_number} обновлена")

    def remove_selected(self) -> bool:
        """
        Удаляет выбранную строку.

        Returns:
            True, если удаление выполнено, иначе False.
        """
        row = self.currentRow()
        if row < 0:
            return False
        self.removeRow(row)
        self.dataChanged.emit()
        logger.debug(f"Удалена строка {row}")
        return True

    def get_coordinates(self) -> List[Tuple[float, float]]:
        """
        Извлекает координаты из таблицы в виде списка кортежей (x, y).

        Returns:
            Список координат.
        """
        coords = []
        for row in range(self.rowCount()):
            try:
                x = float(self.item(row, 1).text())
                y = float(self.item(row, 2).text())
                coords.append((x, y))
            except (ValueError, AttributeError):
                continue
        return coords

    def check_geometry(self) -> Tuple[bool, bool, float]:
        """
        Проверяет геометрию по текущим координатам:
        - замкнутость
        - самопересечения
        - площадь

        Returns:
            Кортеж (замкнуто, нет самопересечений, площадь).
            Если недостаточно точек, возвращает (False, False, 0.0).
        """
        coords = self.get_coordinates()
        if len(coords) < 3:
            return False, False, 0.0
        closed = is_closed(coords)
        self_intersects = is_self_intersecting(coords)
        area = calculate_area(coords)
        return closed, not self_intersects, area

    def _show_context_menu(self, pos):
        """Отображает контекстное меню для таблицы."""
        menu = QMenu(self)
        add_action = QAction("Добавить точку", self)
        add_action.triggered.connect(self._on_add_triggered)
        menu.addAction(add_action)

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self._on_edit_triggered)
        if self.currentRow() < 0:
            edit_action.setEnabled(False)
        menu.addAction(edit_action)

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self._on_delete_triggered)
        if self.currentRow() < 0:
            delete_action.setEnabled(False)
        menu.addAction(delete_action)

        menu.addSeparator()

        check_action = QAction("Проверить геометрию", self)
        check_action.triggered.connect(self._on_check_triggered)
        menu.addAction(check_action)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _on_add_triggered(self):
        """Обработчик добавления точки – открывает диалог."""
        # Создаём новую точку с номером следующим за максимальным
        current_rows = self.rowCount()
        next_num = 1
        if current_rows > 0:
            last_item = self.item(current_rows - 1, 0)
            if last_item:
                next_num = int(last_item.text()) + 1
        point = CharacteristicPoint(point_number=next_num, x=0.0, y=0.0)
        dlg = PointDialog(self, point)
        if dlg.exec():
            self.add_point(point)

    def _on_edit_triggered(self):
        """Обработчик редактирования выбранной точки."""
        row = self.currentRow()
        if row < 0:
            return
        # Нужно получить точку из внешнего источника. В данной реализации
        # предполагается, что точки хранятся снаружи, а таблица только отображает.
        # Поэтому мы не можем просто так взять объект. На практике этот метод
        # должен быть переопределён через сигнал или вызываться из родительского виджета.
        # Для корректной работы здесь нужно либо хранить список точек в самом виджете,
        # либо передавать точку через внешний вызов. Оставим заглушку.
        QMessageBox.information(self, "Информация", "Редактирование должно обрабатываться внешним кодом")

    def _on_delete_triggered(self):
        """Обработчик удаления."""
        self.remove_selected()

    def _on_check_triggered(self):
        """Обработчик проверки геометрии."""
        closed, no_self_intersect, area = self.check_geometry()
        msg = f"Замкнутость: {'да' if closed else 'нет'}\n"
        msg += f"Самопересечения: {'отсутствуют' if no_self_intersect else 'обнаружены'}\n"
        msg += f"Площадь: {area:.2f} кв.м"
        QMessageBox.information(self, "Результат проверки", msg)