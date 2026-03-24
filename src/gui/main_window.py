# src/gui/main_window.py
# Главное окно приложения «Межевой план».
# Содержит меню, панель инструментов, панель проектов слева,
# рабочую область с вкладками справа и статусную строку.

import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeView, QMessageBox, QFileDialog,
    QMenuBar, QMenu, QApplication, QSplitter, QListWidget,
    QTabWidget, QLabel, QStatusBar
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal, Slot

from sqlalchemy.orm import Session

from ..models import Project, Parcel
from ..services.project_service import ProjectService
from ..services.import_service import import_coordinates_from_csv, import_from_kml
from ..services.export_service import ExportService
from ..services.geometry_service import is_closed, is_self_intersecting, calculate_area
from ..services.validation_service import ValidationService
from ..utils.logger import get_logger
from .dialogs.project_dialog import ProjectDialog
from .dialogs.parcel_dialog import ParcelDialog
from .dialogs.customer_engineer_dialog import CustomerEngineerDialog
from .widgets.parcel_table import ParcelTableModel
from .widgets.coordinate_table import CoordinateTable  # если есть, но пока не используется

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Главное окно приложения.
    Содержит:
    - Меню: Файл, Правка, Вид, Проект, Справка.
    - Панель инструментов с кнопками: Создать, Открыть, Сохранить, Генерация, Валидация.
    - Левая панель: список проектов.
    - Правая рабочая область: вкладки (Участки, Координаты, Документы и др.).
    - Статусная строка: информация о текущем проекте и состоянии.
    """

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.project_service = ProjectService(session)
        self.current_project: Project | None = None
        self.unsaved_changes = False  # флаг наличия несохранённых изменений

        self.setWindowTitle("Межевой план")
        self.resize(1300, 800)

        # Создаём меню
        self._create_menu()

        # Создаём панель инструментов
        self._create_toolbar()

        # Создаём центральный виджет с разделителем
        self._create_central_widget()

        # Создаём статусную строку
        self._create_status_bar()

        # Загружаем список проектов в левую панель
        self._refresh_project_list()

        # Автоматически открываем первый проект при запуске
        self._open_first_project()

        logger.info("Главное окно инициализировано")

    def _create_menu(self):
        """Создаёт строку меню."""
        menubar = self.menuBar()

        # === Меню "Файл" ===
        file_menu = menubar.addMenu("&Файл")

        # Импорт
        import_menu = file_menu.addMenu("&Импорт")
        import_csv_action = QAction("Координаты из &CSV", self)
        import_csv_action.triggered.connect(self.import_csv)
        import_menu.addAction(import_csv_action)

        import_kml_action = QAction("Границы из &KML", self)
        import_kml_action.triggered.connect(self.import_kml)
        import_menu.addAction(import_kml_action)

        # Экспорт
        export_menu = file_menu.addMenu("&Экспорт")
        export_xml_action = QAction("Межевой план в &XML", self)
        export_xml_action.triggered.connect(self.export_xml)
        export_menu.addAction(export_xml_action)

        export_csv_action = QAction("Координаты в &CSV", self)
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)

        file_menu.addSeparator()
        exit_action = QAction("&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === Меню "Правка" ===
        edit_menu = menubar.addMenu("&Правка")
        # Действия с участками
        add_parcel_action = QAction("&Добавить участок", self)
        add_parcel_action.setShortcut("Ins")
        add_parcel_action.triggered.connect(self.add_parcel)
        edit_menu.addAction(add_parcel_action)

        edit_parcel_action = QAction("&Редактировать участок", self)
        edit_parcel_action.setShortcut("F2")
        edit_parcel_action.triggered.connect(self.edit_parcel)
        edit_menu.addAction(edit_parcel_action)

        delete_parcel_action = QAction("&Удалить участок", self)
        delete_parcel_action.setShortcut("Del")
        delete_parcel_action.triggered.connect(self.delete_parcel)
        edit_menu.addAction(delete_parcel_action)

        edit_menu.addSeparator()
        # Управление справочниками
        manage_engineers_action = QAction("&Кадастровые инженеры", self)
        manage_engineers_action.triggered.connect(self.manage_engineers)
        edit_menu.addAction(manage_engineers_action)

        manage_customers_action = QAction("&Заказчики", self)
        manage_customers_action.triggered.connect(self.manage_customers)
        edit_menu.addAction(manage_customers_action)

        # === Меню "Вид" ===
        view_menu = menubar.addMenu("&Вид")
        # Можно добавить действия для переключения вкладок и т.п.

        # === Меню "Проект" ===
        project_menu = menubar.addMenu("&Проект")
        new_project_action = QAction("&Создать проект", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self.new_project)
        project_menu.addAction(new_project_action)

        open_project_action = QAction("&Открыть проект", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open_project)
        project_menu.addAction(open_project_action)

        save_project_action = QAction("&Сохранить проект", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.triggered.connect(self.save_project)
        project_menu.addAction(save_project_action)

        project_menu.addSeparator()
        generate_action = QAction("&Генерация XML", self)
        generate_action.triggered.connect(self.export_xml)
        project_menu.addAction(generate_action)

        validate_action = QAction("&Валидация XML", self)
        validate_action.triggered.connect(self.validate_xml)
        project_menu.addAction(validate_action)

        # === Меню "Справка" ===
        help_menu = menubar.addMenu("&Справка")
        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Создаёт панель инструментов с кнопками."""
        toolbar = self.addToolBar("Основная")
        toolbar.setMovable(False)

        # Кнопки
        btn_new = QAction("Создать", self)
        btn_new.triggered.connect(self.new_project)
        toolbar.addAction(btn_new)

        btn_open = QAction("Открыть", self)
        btn_open.triggered.connect(self.open_project)
        toolbar.addAction(btn_open)

        btn_save = QAction("Сохранить", self)
        btn_save.triggered.connect(self.save_project)
        toolbar.addAction(btn_save)

        toolbar.addSeparator()

        btn_generate = QAction("Генерация", self)
        btn_generate.triggered.connect(self.export_xml)
        toolbar.addAction(btn_generate)

        btn_validate = QAction("Валидация", self)
        btn_validate.triggered.connect(self.validate_xml)
        toolbar.addAction(btn_validate)

    def _create_central_widget(self):
        """Создаёт центральную область с разделителем: слева список проектов, справа вкладки."""
        central = QWidget()
        self.setCentralWidget(central)

        # Основной горизонтальный разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        # Левая панель: список проектов
        self.project_list = QListWidget()
        self.project_list.setMaximumWidth(250)
        self.project_list.itemClicked.connect(self.on_project_selected)
        splitter.addWidget(self.project_list)

        # Правая панель: вкладки
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # Вкладка "Участки"
        self.parcels_tab = self._create_parcels_tab()
        self.tab_widget.addTab(self.parcels_tab, "Участки")

        # Вкладка "Координаты" (может быть связана с выбранным участком)
        self.coords_tab = QWidget()
        self.tab_widget.addTab(self.coords_tab, "Координаты")
        # Здесь можно разместить CoordinateTable, но для простоты оставим пустым

        # Вкладка "Документы"
        self.documents_tab = QWidget()
        self.tab_widget.addTab(self.documents_tab, "Документы")

        # Вкладка "Согласование"
        self.agreement_tab = QWidget()
        self.tab_widget.addTab(self.agreement_tab, "Согласование")

        # Устанавливаем пропорции: левая панель 1, правая 3
        splitter.setSizes([250, 750])

    def _create_parcels_tab(self) -> QWidget:
        """Создаёт вкладку с таблицей участков и панелью инструментов для участков."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Локальная панель инструментов для участков
        toolbar = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self.add_parcel)
        toolbar.addWidget(btn_add)

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(self.edit_parcel)
        toolbar.addWidget(btn_edit)

        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self.delete_parcel)
        toolbar.addWidget(btn_delete)

        btn_check = QPushButton("Проверить геометрию")
        btn_check.clicked.connect(self.validate_geometry)
        toolbar.addWidget(btn_check)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Таблица участков
        self.parcel_table = QTreeView()
        self.parcel_model = ParcelTableModel([])
        self.parcel_table.setModel(self.parcel_model)
        self.parcel_table.setSelectionBehavior(QTreeView.SelectRows)
        self.parcel_table.setSelectionMode(QTreeView.SingleSelection)
        layout.addWidget(self.parcel_table)

        return widget

    def _create_status_bar(self):
        """Создаёт статусную строку с тремя сегментами."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Создаём три метки
        self.status_label = QLabel("Готов")
        self.project_status_label = QLabel("Проект: не выбран")
        self.save_status_label = QLabel("")

        # Добавляем их в статусную строку
        self.status_bar.addWidget(self.status_label, 1)          # растягивается
        self.status_bar.addWidget(self.project_status_label, 1)
        self.status_bar.addWidget(self.save_status_label, 1)

    def update_status_bar(self):
        """Обновляет статусную строку в зависимости от текущего проекта."""
        if self.current_project:
            self.project_status_label.setText(f"Проект: {self.current_project.name}")
            if self.unsaved_changes:
                self.save_status_label.setText("⚠️ Не сохранено")
                self.save_status_label.setStyleSheet("color: orange;")
            else:
                self.save_status_label.setText("✅ Сохранено")
                self.save_status_label.setStyleSheet("color: green;")
        else:
            self.project_status_label.setText("Проект: не выбран")
            self.save_status_label.setText("")
        self.status_label.setText("Готов")

    def set_unsaved_changes(self, value: bool = True):
        """Устанавливает флаг несохранённых изменений и обновляет статус."""
        self.unsaved_changes = value
        self.update_status_bar()

    # ==================== Работа со списком проектов ====================

    def _refresh_project_list(self):
        """Обновляет список проектов в левой панели."""
        self.project_list.clear()
        projects = self.project_service.get_all_projects()
        for proj in projects:
            self.project_list.addItem(f"{proj.id}: {proj.name} ({proj.status})")
            # Можно сохранить id в данных элемента
            item = self.project_list.item(self.project_list.count() - 1)
            item.setData(Qt.UserRole, proj.id)

    def on_project_selected(self, item):
        """Обработчик выбора проекта из списка."""
        project_id = item.data(Qt.UserRole)
        if project_id:
            project = self.project_service.get_project(project_id)
            if project:
                self.current_project = project
                self.refresh_parcel_list()
                self.update_status_bar()
                logger.info(f"Выбран проект {project.id}")

    def _open_first_project(self):
        """Автоматически выбирает первый проект при запуске."""
        projects = self.project_service.get_all_projects()
        if projects:
            self.current_project = projects[0]
            self.refresh_parcel_list()
            # Выделяем в списке
            for i in range(self.project_list.count()):
                if self.project_list.item(i).data(Qt.UserRole) == projects[0].id:
                    self.project_list.setCurrentRow(i)
                    break
        self.update_status_bar()

    # ==================== Действия с проектами ====================

    def new_project(self):
        """Создание нового проекта."""
        dlg = ProjectDialog(self, self.session)
        if dlg.exec():
            data = dlg.get_data()
            project = self.project_service.create_project(
                name=data["name"],
                engineer_id=data["engineer_id"],
                customer_ids=data["customer_ids"],
                description=data.get("description")
            )
            if project:
                self._refresh_project_list()
                # Выбираем созданный проект
                self.current_project = project
                self.refresh_parcel_list()
                self.set_unsaved_changes(False)
                self.update_status_bar()
                logger.info(f"Создан проект {project.id}")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать проект")

    def open_project(self):
        """Открытие существующего проекта через диалог выбора."""
        # Используем QInputDialog для выбора из списка проектов
        from PySide6.QtWidgets import QInputDialog
        projects = self.project_service.get_all_projects()
        if not projects:
            QMessageBox.information(self, "Информация", "Нет сохранённых проектов")
            return
        items = [f"{p.id}: {p.name} ({p.status})" for p in projects]
        ok, index = QInputDialog.getItem(self, "Выбор проекта", "Выберите проект:", items, 0, False)
        if ok and index >= 0:
            project_id = projects[index].id
            self.current_project = self.project_service.get_project(project_id)
            self.refresh_parcel_list()
            # Выделяем в левом списке
            for i in range(self.project_list.count()):
                if self.project_list.item(i).data(Qt.UserRole) == project_id:
                    self.project_list.setCurrentRow(i)
                    break
            self.set_unsaved_changes(False)
            self.update_status_bar()
            logger.info(f"Открыт проект {project_id}")

    def save_project(self):
        """Сохранение текущего проекта."""
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        if self.project_service.save_project(self.current_project):
            self.set_unsaved_changes(False)
            self.status_label.setText("Проект сохранён")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить проект")

    # ==================== Действия с участками ====================

    def add_parcel(self):
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        dlg = ParcelDialog(self, self.session)
        if dlg.exec():
            parcel = dlg.get_parcel()
            self.current_project.parcels.append(parcel)
            self.session.add(parcel)
            self.refresh_parcel_list()
            self.set_unsaved_changes(True)
            logger.info(f"Добавлен участок {parcel.id}")

    def edit_parcel(self):
        if not self.current_project:
            return
        index = self.parcel_table.currentIndex()
        if not index.isValid():
            QMessageBox.information(self, "Информация", "Выберите участок для редактирования")
            return
        parcel = self.parcel_model.get_parcel(index.row())
        dlg = ParcelDialog(self, self.session, parcel)
        if dlg.exec():
            self.refresh_parcel_list()
            self.set_unsaved_changes(True)
            logger.info(f"Участок {parcel.id} отредактирован")

    def delete_parcel(self):
        if not self.current_project:
            return
        index = self.parcel_table.currentIndex()
        if not index.isValid():
            QMessageBox.information(self, "Информация", "Выберите участок для удаления")
            return
        parcel = self.parcel_model.get_parcel(index.row())
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить участок {parcel.cadastral_number or '(без номера)'}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.session.delete(parcel)
            self.refresh_parcel_list()
            self.set_unsaved_changes(True)
            logger.info(f"Участок {parcel.id} удалён")

    def refresh_parcel_list(self):
        if self.current_project:
            self.parcel_model.set_parcels(self.current_project.parcels)
        else:
            self.parcel_model.set_parcels([])

    # ==================== Импорт/Экспорт ====================

    def import_csv(self):
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "Выберите CSV-файл", "", "CSV файлы (*.csv);;Все файлы (*)")
        if not filepath:
            return
        try:
            coords = import_coordinates_from_csv(filepath)
            if not coords:
                QMessageBox.warning(self, "Импорт", "Не удалось извлечь координаты из файла")
                return
            from ..models import Parcel, ParcelStatus, CharacteristicPoint
            parcel = Parcel(
                status=ParcelStatus.NEW,
                cadastral_block="",
                land_category_code="003001000000",
                address_region="77",
                address_or_location=1
            )
            for i, (x, y) in enumerate(coords, start=1):
                point = CharacteristicPoint(point_number=i, x=x, y=y)
                parcel.points.append(point)
            self.current_project.parcels.append(parcel)
            self.session.add(parcel)
            self.refresh_parcel_list()
            self.set_unsaved_changes(True)
            self.status_label.setText(f"Импортировано {len(coords)} точек из CSV")
            logger.info(f"Импорт CSV: добавлен новый участок с {len(coords)} точками")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            logger.exception("Ошибка импорта CSV")

    def import_kml(self):
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте или откройте проект")
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "Выберите KML-файл", "", "KML файлы (*.kml);;Все файлы (*)")
        if not filepath:
            return
        try:
            coords = import_from_kml(filepath)
            from ..models import Parcel, ParcelStatus, CharacteristicPoint
            parcel = Parcel(
                status=ParcelStatus.NEW,
                cadastral_block="",
                land_category_code="003001000000",
                address_region="77",
                address_or_location=1
            )
            for i, (x, y) in enumerate(coords, start=1):
                point = CharacteristicPoint(point_number=i, x=x, y=y)
                parcel.points.append(point)
            self.current_project.parcels.append(parcel)
            self.session.add(parcel)
            self.refresh_parcel_list()
            self.set_unsaved_changes(True)
            self.status_label.setText(f"Импортировано {len(coords)} точек из KML")
            logger.info(f"Импорт KML: добавлен новый участок с {len(coords)} точками")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            logger.exception("Ошибка импорта KML")

    def export_xml(self):
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML межевого плана", "",
            "XML файлы (*.xml);;Все файлы (*)"
        )
        if not filepath:
            return
        service = ExportService(self.current_project)
        if service.export_to_xml(filepath):
            QMessageBox.information(self, "Экспорт", f"XML сохранён в {filepath}")
            self.status_label.setText("XML сгенерирован")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось экспортировать XML")

    def export_csv(self):
        if not self.current_project:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого проекта")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить координаты в CSV", "",
            "CSV файлы (*.csv);;Все файлы (*)"
        )
        if not filepath:
            return
        service = ExportService(self.current_project)
        if service.export_coordinates_to_csv(filepath):
            QMessageBox.information(self, "Экспорт", f"Координаты сохранены в {filepath}")
            self.status_label.setText("Координаты экспортированы")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось экспортировать координаты")

    def validate_xml(self):
        """Валидация последнего сгенерированного XML или выбор файла."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Выберите XML-файл для валидации", "", "XML файлы (*.xml)")
        if not filepath:
            return
        validator = ValidationService()
        success, errors = validator.validate_xml(filepath)
        if success:
            QMessageBox.information(self, "Валидация", "XML успешно прошёл проверку")
        else:
            msg = "Ошибки валидации:\n" + "\n".join(errors)
            QMessageBox.critical(self, "Ошибка валидации", msg)

    # ==================== Проверка геометрии ====================

    def validate_geometry(self):
        index = self.parcel_table.currentIndex()
        if not index.isValid():
            QMessageBox.information(self, "Информация", "Выберите участок для проверки")
            return
        parcel = self.parcel_model.get_parcel(index.row())
        if parcel.contours:
            points = parcel.contours[0].points
        else:
            points = parcel.points
        if len(points) < 3:
            QMessageBox.warning(self, "Проверка", "Недостаточно точек для проверки (минимум 3)")
            return
        coords = [(p.x, p.y) for p in points]
        closed = is_closed(coords)
        self_intersects = is_self_intersecting(coords)
        area = calculate_area(coords)
        msg = f"Проверка участка {parcel.cadastral_number or '(без номера)'}:\n"
        msg += f"Замкнутость: {'да' if closed else 'нет'}\n"
        msg += f"Самопересечения: {'обнаружены' if self_intersects else 'отсутствуют'}\n"
        msg += f"Площадь: {area:.2f} кв.м"
        QMessageBox.information(self, "Результат проверки", msg)

    # ==================== Управление справочниками ====================

    def manage_engineers(self):
        dlg = CustomerEngineerDialog(self, self.session, mode='engineer')
        dlg.exec()

    def manage_customers(self):
        dlg = CustomerEngineerDialog(self, self.session, mode='customer')
        dlg.exec()

    # ==================== О программе ====================

    def about(self):
        about_text = """
        <h2>Межевой план</h2>
        <p><b>Версия:</b> 1.0</p>
        <p><b>Разработчик:</b> Абрамов Сергей Николаевич</p>
        <p><b>Группа:</b> 2024-ФГиИБ-ИС-3см</p>
        <p><b>Факультет:</b> Геоинформатики и информационной безопасности</p>
        <p><b>Кафедра:</b> Информационно-измерительных систем</p>
        <p><b>Направление подготовки:</b> 09.04.02 Информационные системы и технологии</p>
        <p><b>Выпускная квалификационная работа:</b> Проектирование приложения «Разработка проекта межевания»</p>
        <p>Программа для создания и редактирования межевых планов в формате XML, соответствующем схеме Росреестра MP_v09.xsd.</p>
        <p>© 2026</p>
        """
        QMessageBox.about(self, "О программе", about_text)

    # ==================== Обработка закрытия ====================

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Есть несохранённые изменения. Сохранить перед выходом?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_project()
                if self.unsaved_changes:  # если сохранить не удалось
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        event.accept()