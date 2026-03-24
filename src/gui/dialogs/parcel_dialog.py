# src/gui/dialogs/parcel_dialog.py
# Диалог для создания и редактирования земельного участка.
# Содержит три вкладки: "Основное", "Координаты", "Адрес".
# Позволяет вводить кадастровый номер, категорию земель, статус, адрес,
# а также редактировать список характерных точек с возможностью проверки геометрии.

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QLineEdit, QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QMessageBox, QHeaderView, QWidget,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt

from sqlalchemy.orm import Session

from ...models import (
    Parcel, ParcelStatus, LandCategory, AllowedUse, Region,
    CharacteristicPoint, Contour
)
from ...services.geometry_service import calculate_area, is_closed, is_self_intersecting
from ...utils.logger import get_logger
from .point_dialog import PointDialog

logger = get_logger(__name__)


class ParcelDialog(QDialog):
    """
    Диалог редактирования земельного участка.
    Поддерживает как создание нового участка, так и редактирование существующего.
    """

    def __init__(self, parent, session: Session, parcel: Parcel = None):
        """
        Инициализация диалога.

        Args:
            parent: Родительский виджет.
            session: Сессия SQLAlchemy.
            parcel: Существующий участок (если редактируется). Если None, создаётся новый.
        """
        super().__init__(parent)
        self.session = session
        self.parcel = parcel if parcel is not None else Parcel(status=ParcelStatus.NEW)

        self.setWindowTitle("Редактирование участка" if parcel else "Новый участок")
        self.resize(800, 600)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Создание интерфейса диалога."""
        main_layout = QVBoxLayout(self)

        # Создаём вкладки
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Вкладка "Основное"
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Основное")

        # Вкладка "Координаты"
        coords_tab = self._create_coords_tab()
        tabs.addTab(coords_tab, "Координаты")

        # Вкладка "Адрес"
        address_tab = self._create_address_tab()
        tabs.addTab(address_tab, "Адрес")

        # Кнопки OK/Отмена
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _create_basic_tab(self) -> QWidget:
        """Создаёт вкладку с основными атрибутами участка."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Кадастровый номер (строка)
        self.cadastral_number_edit = QLineEdit()
        self.cadastral_number_edit.setPlaceholderText("AA:BB:CCCCCC:K")
        layout.addRow("Кадастровый номер:", self.cadastral_number_edit)

        # Статус участка (выбор из перечисления)
        self.status_combo = QComboBox()
        for status in ParcelStatus:
            self.status_combo.addItem(status.value, status)
        layout.addRow("Статус:", self.status_combo)

        # Номер кадастрового квартала (обязательное поле)
        self.cadastral_block_edit = QLineEdit()
        self.cadastral_block_edit.setPlaceholderText("AA:BB:CCCCCC")
        layout.addRow("Кадастровый квартал:", self.cadastral_block_edit)

        # Категория земель (выбор из справочника)
        self.category_combo = QComboBox()
        categories = self.session.query(LandCategory).order_by(LandCategory.code).all()
        self.category_combo.addItem("-- Не выбрано --", None)
        for cat in categories:
            self.category_combo.addItem(f"{cat.code} – {cat.name}", cat.code)
        layout.addRow("Категория земель:", self.category_combo)

        # Вид разрешённого использования (может быть код или текст)
        # Сначала выбираем: по классификатору или произвольный текст
        self.use_type_combo = QComboBox()
        self.use_type_combo.addItem("По классификатору", "code")
        self.use_type_combo.addItem("Произвольный текст", "text")
        self.use_type_combo.currentIndexChanged.connect(self._on_use_type_changed)
        layout.addRow("Тип ВРИ:", self.use_type_combo)

        # Комбобокс для кодов
        self.allowed_use_combo = QComboBox()
        allowed_uses = self.session.query(AllowedUse).order_by(AllowedUse.code).all()
        self.allowed_use_combo.addItem("-- Не выбрано --", None)
        for au in allowed_uses:
            self.allowed_use_combo.addItem(f"{au.code} – {au.name}", au.code)
        layout.addRow("Код ВРИ:", self.allowed_use_combo)

        # Текстовое поле для произвольного ВРИ
        self.permitted_use_text_edit = QLineEdit()
        self.permitted_use_text_edit.setPlaceholderText("Введите текст разрешённого использования")
        layout.addRow("Текст ВРИ:", self.permitted_use_text_edit)

        # Площадь (вычисляется, но можно вручную)
        self.area_spin = QDoubleSpinBox()
        self.area_spin.setRange(0, 1e9)
        self.area_spin.setDecimals(2)
        self.area_spin.setSuffix(" кв.м")
        layout.addRow("Площадь:", self.area_spin)

        # Погрешность площади
        self.area_inaccuracy_spin = QDoubleSpinBox()
        self.area_inaccuracy_spin.setRange(0, 1e9)
        self.area_inaccuracy_spin.setDecimals(2)
        self.area_inaccuracy_spin.setSuffix(" кв.м")
        layout.addRow("Погрешность площади:", self.area_inaccuracy_spin)

        # Формула площади
        self.area_formula_edit = QLineEdit()
        layout.addRow("Формула площади:", self.area_formula_edit)

        # Иные сведения (Note) – многострочное поле
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(100)
        layout.addRow("Примечание:", self.note_edit)

        return widget

    def _create_coords_tab(self) -> QWidget:
        """Создаёт вкладку для редактирования координат характерных точек."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Таблица точек
        self.point_table = QTableWidget(0, 4)  # 4 колонки: №, X, Y, СКП
        self.point_table.setHorizontalHeaderLabels(["№", "X", "Y", "СКП"])
        self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.point_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.point_table)

        # Кнопки управления точками
        btn_layout = QHBoxLayout()
        self.btn_add_point = QPushButton("Добавить точку")
        self.btn_add_point.clicked.connect(self._add_point)
        btn_layout.addWidget(self.btn_add_point)

        self.btn_edit_point = QPushButton("Редактировать")
        self.btn_edit_point.clicked.connect(self._edit_point)
        btn_layout.addWidget(self.btn_edit_point)

        self.btn_delete_point = QPushButton("Удалить")
        self.btn_delete_point.clicked.connect(self._delete_point)
        btn_layout.addWidget(self.btn_delete_point)

        self.btn_check_geom = QPushButton("Проверить геометрию")
        self.btn_check_geom.clicked.connect(self._check_geometry)
        btn_layout.addWidget(self.btn_check_geom)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_address_tab(self) -> QWidget:
        """Создаёт вкладку для ввода структурированного адреса."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Код ФИАС
        self.fias_edit = QLineEdit()
        layout.addRow("Код ФИАС:", self.fias_edit)

        # Почтовый индекс
        self.postal_code_edit = QLineEdit()
        layout.addRow("Почтовый индекс:", self.postal_code_edit)

        # Регион (субъект РФ) – обязательное поле
        self.region_combo = QComboBox()
        regions = self.session.query(Region).order_by(Region.code).all()
        self.region_combo.addItem("-- Не выбрано --", None)
        for reg in regions:
            self.region_combo.addItem(f"{reg.code} – {reg.name}", reg.code)
        layout.addRow("Регион:", self.region_combo)

        # Район
        self.district_edit = QLineEdit()
        layout.addRow("Район:", self.district_edit)

        # Муниципальное образование
        self.city_edit = QLineEdit()
        layout.addRow("Муниципальное образование:", self.city_edit)

        # Городской район
        self.urban_district_edit = QLineEdit()
        layout.addRow("Городской район:", self.urban_district_edit)

        # Сельсовет
        self.soviet_village_edit = QLineEdit()
        layout.addRow("Сельсовет:", self.soviet_village_edit)

        # Населённый пункт
        self.locality_edit = QLineEdit()
        layout.addRow("Населённый пункт:", self.locality_edit)

        # Улица
        self.street_edit = QLineEdit()
        layout.addRow("Улица:", self.street_edit)

        # Дом (Level1)
        self.level1_edit = QLineEdit()
        layout.addRow("Дом:", self.level1_edit)

        # Корпус (Level2)
        self.level2_edit = QLineEdit()
        layout.addRow("Корпус:", self.level2_edit)

        # Строение (Level3)
        self.level3_edit = QLineEdit()
        layout.addRow("Строение:", self.level3_edit)

        # Квартира
        self.apartment_edit = QLineEdit()
        layout.addRow("Квартира:", self.apartment_edit)

        # Дополнительные сведения (Other)
        self.other_edit = QTextEdit()
        self.other_edit.setMaximumHeight(80)
        layout.addRow("Доп. сведения:", self.other_edit)

        # Неформализованное описание (Note)
        self.address_note_edit = QTextEdit()
        self.address_note_edit.setMaximumHeight(80)
        layout.addRow("Неформализованное описание:", self.address_note_edit)

        # Признак "адрес/местоположение"
        self.address_or_location_combo = QComboBox()
        self.address_or_location_combo.addItem("Присвоенный адрес", 1)
        self.address_or_location_combo.addItem("Описание местоположения", 0)
        layout.addRow("Тип:", self.address_or_location_combo)

        return widget

    def _load_data(self):
        """Заполняет поля диалога данными из self.parcel."""
        # Основная вкладка
        self.cadastral_number_edit.setText(self.parcel.cadastral_number or "")
        idx = self.status_combo.findData(self.parcel.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        self.cadastral_block_edit.setText(self.parcel.cadastral_block or "")

        # Категория
        if self.parcel.land_category_code:
            idx = self.category_combo.findData(self.parcel.land_category_code)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        # Вид разрешённого использования
        if self.parcel.permitted_use_code:
            self.use_type_combo.setCurrentIndex(0)  # по классификатору
            idx = self.allowed_use_combo.findData(self.parcel.permitted_use_code)
            if idx >= 0:
                self.allowed_use_combo.setCurrentIndex(idx)
            self.permitted_use_text_edit.setText(self.parcel.permitted_use_text or "")
        elif self.parcel.permitted_use_text:
            self.use_type_combo.setCurrentIndex(1)  # текст
            self.permitted_use_text_edit.setText(self.parcel.permitted_use_text)
        else:
            self.use_type_combo.setCurrentIndex(0)
            self.allowed_use_combo.setCurrentIndex(0)

        self._on_use_type_changed()  # обновить видимость

        self.area_spin.setValue(self.parcel.area or 0.0)
        self.area_inaccuracy_spin.setValue(self.parcel.area_inaccuracy or 0.0)
        self.area_formula_edit.setText(self.parcel.area_formula or "")
        self.note_edit.setPlainText(self.parcel.note or "")

        # Координаты – загружаем точки (упрощённо, если нет контуров)
        # В реальном проекте нужно учитывать многоконтурность. Для простоты работаем с points.
        self._refresh_point_table()

        # Адрес
        self.fias_edit.setText(self.parcel.address_fias or "")
        self.postal_code_edit.setText(self.parcel.address_postal_code or "")
        if self.parcel.address_region:
            idx = self.region_combo.findData(self.parcel.address_region)
            if idx >= 0:
                self.region_combo.setCurrentIndex(idx)
        self.district_edit.setText(self.parcel.address_district or "")
        self.city_edit.setText(self.parcel.address_city or "")
        self.urban_district_edit.setText(self.parcel.address_urban_district or "")
        self.soviet_village_edit.setText(self.parcel.address_soviet_village or "")
        self.locality_edit.setText(self.parcel.address_locality or "")
        self.street_edit.setText(self.parcel.address_street or "")
        self.level1_edit.setText(self.parcel.address_level1 or "")
        self.level2_edit.setText(self.parcel.address_level2 or "")
        self.level3_edit.setText(self.parcel.address_level3 or "")
        self.apartment_edit.setText(self.parcel.address_apartment or "")
        self.other_edit.setPlainText(self.parcel.address_other or "")
        self.address_note_edit.setPlainText(self.parcel.address_note or "")
        idx = self.address_or_location_combo.findData(self.parcel.address_or_location)
        if idx >= 0:
            self.address_or_location_combo.setCurrentIndex(idx)

    def _refresh_point_table(self):
        """Обновляет таблицу точек из self.parcel.points."""
        points = sorted(self.parcel.points, key=lambda p: p.point_number)
        self.point_table.setRowCount(len(points))
        for i, p in enumerate(points):
            self.point_table.setItem(i, 0, QTableWidgetItem(str(p.point_number)))
            self.point_table.setItem(i, 1, QTableWidgetItem(f"{p.x:.2f}"))
            self.point_table.setItem(i, 2, QTableWidgetItem(f"{p.y:.2f}"))
            self.point_table.setItem(i, 3, QTableWidgetItem(f"{p.delta:.2f}" if p.delta else ""))

    def _on_use_type_changed(self):
        """Обработка переключения типа ВРИ (код/текст)."""
        is_code = self.use_type_combo.currentData() == 'code'
        self.allowed_use_combo.setEnabled(is_code)
        self.permitted_use_text_edit.setEnabled(not is_code)

    def _add_point(self):
        """Добавление новой характерной точки."""
        # Определяем следующий номер
        next_num = max([p.point_number for p in self.parcel.points], default=0) + 1
        point = CharacteristicPoint(point_number=next_num, x=0, y=0)
        dlg = PointDialog(self, point)
        if dlg.exec():
            self.parcel.points.append(point)
            self._refresh_point_table()
            logger.debug(f"Добавлена точка {point.point_number}")

    def _edit_point(self):
        """Редактирование выбранной точки."""
        current_row = self.point_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите точку для редактирования")
            return
        point = self.parcel.points[current_row]
        dlg = PointDialog(self, point)
        if dlg.exec():
            self._refresh_point_table()

    def _delete_point(self):
        """Удаление выбранной точки."""
        current_row = self.point_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите точку для удаления")
            return
        confirm = QMessageBox.question(self, "Подтверждение", "Удалить выбранную точку?")
        if confirm == QMessageBox.Yes:
            del self.parcel.points[current_row]
            self._refresh_point_table()

    def _check_geometry(self):
        """Проверка геометрии по текущим координатам."""
        coords = []
        for row in range(self.point_table.rowCount()):
            try:
                x = float(self.point_table.item(row, 1).text())
                y = float(self.point_table.item(row, 2).text())
                coords.append((x, y))
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Ошибка", f"Некорректные координаты в строке {row+1}")
                return

        if len(coords) < 3:
            QMessageBox.warning(self, "Проверка", "Недостаточно точек (минимум 3)")
            return

        closed = is_closed(coords)
        self_intersects = is_self_intersecting(coords)
        area = calculate_area(coords)

        msg = f"Замкнутость: {'да' if closed else 'нет'}\n"
        msg += f"Самопересечения: {'обнаружены' if self_intersects else 'отсутствуют'}\n"
        msg += f"Площадь: {area:.2f} кв.м"
        QMessageBox.information(self, "Результат проверки", msg)

        # Обновляем поле площади
        self.area_spin.setValue(area)

    def validate_and_accept(self):
        """Проверка заполнения обязательных полей и сохранение данных."""
        # Проверка обязательных полей
        if not self.cadastral_block_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Номер кадастрового квартала обязателен.")
            return

        if self.category_combo.currentData() is None:
            QMessageBox.warning(self, "Предупреждение", "Выберите категорию земель.")
            return

        if self.region_combo.currentData() is None:
            QMessageBox.warning(self, "Предупреждение", "Выберите регион (субъект РФ).")
            return

        # Сбор данных
        self.parcel.cadastral_number = self.cadastral_number_edit.text().strip() or None
        self.parcel.status = self.status_combo.currentData()
        self.parcel.cadastral_block = self.cadastral_block_edit.text().strip()
        self.parcel.land_category_code = self.category_combo.currentData()
        self.parcel.area = self.area_spin.value()
        self.parcel.area_inaccuracy = self.area_inaccuracy_spin.value()
        self.parcel.area_formula = self.area_formula_edit.text().strip() or None
        self.parcel.note = self.note_edit.toPlainText().strip() or None

        # ВРИ
        if self.use_type_combo.currentData() == 'code':
            self.parcel.permitted_use_code = self.allowed_use_combo.currentData()
            self.parcel.permitted_use_text = None
        else:
            self.parcel.permitted_use_code = None
            self.parcel.permitted_use_text = self.permitted_use_text_edit.text().strip() or None

        # Адрес
        self.parcel.address_fias = self.fias_edit.text().strip() or None
        self.parcel.address_postal_code = self.postal_code_edit.text().strip() or None
        self.parcel.address_region = self.region_combo.currentData()
        self.parcel.address_district = self.district_edit.text().strip() or None
        self.parcel.address_city = self.city_edit.text().strip() or None
        self.parcel.address_urban_district = self.urban_district_edit.text().strip() or None
        self.parcel.address_soviet_village = self.soviet_village_edit.text().strip() or None
        self.parcel.address_locality = self.locality_edit.text().strip() or None
        self.parcel.address_street = self.street_edit.text().strip() or None
        self.parcel.address_level1 = self.level1_edit.text().strip() or None
        self.parcel.address_level2 = self.level2_edit.text().strip() or None
        self.parcel.address_level3 = self.level3_edit.text().strip() or None
        self.parcel.address_apartment = self.apartment_edit.text().strip() or None
        self.parcel.address_other = self.other_edit.toPlainText().strip() or None
        self.parcel.address_note = self.address_note_edit.toPlainText().strip() or None
        self.parcel.address_or_location = self.address_or_location_combo.currentData()

        # Точки уже сохранены в self.parcel.points
        # При необходимости можно добавить проверку на замкнутость контура

        self.accept()

    def get_parcel(self) -> Parcel:
        """Возвращает отредактированный участок."""
        return self.parcel