# src/gui/dialogs/project_dialog.py
# Диалог создания и редактирования проекта.
# Позволяет задать название, описание, выбрать кадастрового инженера и одного или нескольких заказчиков.

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox,
    QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from sqlalchemy.orm import Session

from ...models import Project, CadastralEngineer, Customer
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ProjectDialog(QDialog):
    """
    Диалог для создания нового проекта или редактирования существующего.
    Позволяет ввести название, описание, выбрать ответственного инженера
    и одного или нескольких заказчиков.
    """

    def __init__(self, parent, session: Session, project: Project = None):
        """
        Инициализация диалога.

        Args:
            parent: Родительский виджет.
            session: Сессия SQLAlchemy для доступа к БД.
            project: Существующий проект (если редактируется). Если None, создаётся новый.
        """
        super().__init__(parent)
        self.session = session
        self.project = project  # может быть None
        self.setWindowTitle("Новый проект" if project is None else f"Редактирование проекта: {project.name}")
        self.resize(600, 500)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Форма для основных полей
        form_layout = QFormLayout()

        # Название проекта
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название проекта")
        form_layout.addRow("Название:", self.name_edit)

        # Описание (многострочное)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Описание проекта (необязательно)")
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Описание:", self.description_edit)

        # Выбор кадастрового инженера
        engineer_layout = QHBoxLayout()
        self.engineer_combo = QComboBox()
        self.engineer_combo.setMinimumWidth(300)
        engineer_layout.addWidget(self.engineer_combo)

        self.btn_manage_engineers = QPushButton("Управление...")
        self.btn_manage_engineers.clicked.connect(self._manage_engineers)
        engineer_layout.addWidget(self.btn_manage_engineers)

        form_layout.addRow("Кадастровый инженер:", engineer_layout)

        # Выбор заказчиков (множественный выбор)
        customers_layout = QVBoxLayout()
        self.customers_list = QListWidget()
        self.customers_list.setSelectionMode(QListWidget.MultiSelection)
        customers_layout.addWidget(self.customers_list)

        btn_customers_layout = QHBoxLayout()
        self.btn_manage_customers = QPushButton("Управление заказчиками...")
        self.btn_manage_customers.clicked.connect(self._manage_customers)
        btn_customers_layout.addWidget(self.btn_manage_customers)
        btn_customers_layout.addStretch()
        customers_layout.addLayout(btn_customers_layout)

        form_layout.addRow("Заказчики:", customers_layout)

        layout.addLayout(form_layout)

        # Кнопки OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_data(self):
        """Загрузка данных из БД и заполнение элементов интерфейса."""
        # Загрузка инженеров
        engineers = self.session.query(CadastralEngineer).all()
        self.engineer_combo.clear()
        self.engineer_combo.addItem("-- Не выбрано --", None)
        for eng in engineers:
            name = f"{eng.family_name} {eng.first_name} {eng.patronymic or ''}".strip()
            self.engineer_combo.addItem(f"{name} (атт. {eng.attestation_number})", eng.id)

        # Загрузка заказчиков
        customers = self.session.query(Customer).all()
        self.customers_list.clear()
        for cust in customers:
            # Формируем отображаемое имя в зависимости от типа
            if cust.customer_type == 'person':
                name = f"{cust.family_name} {cust.first_name} {cust.patronymic or ''}".strip()
                display = f"{name} (физлицо)"
            elif cust.customer_type == 'organization':
                display = f"{cust.full_name} (юрлицо)"
            elif cust.customer_type == 'governance':
                display = f"{cust.full_name} (орган власти)"
            else:
                display = f"{cust.full_name or ''} (иностранное)"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, cust.id)
            self.customers_list.addItem(item)

        # Если редактируем существующий проект, устанавливаем значения
        if self.project:
            self.name_edit.setText(self.project.name)
            self.description_edit.setPlainText(self.project.description or "")

            # Выбор инженера
            if self.project.engineer_id:
                index = self.engineer_combo.findData(self.project.engineer_id)
                if index >= 0:
                    self.engineer_combo.setCurrentIndex(index)

            # Выбор заказчиков
            selected_ids = [c.id for c in self.project.customers]
            for i in range(self.customers_list.count()):
                item = self.customers_list.item(i)
                cust_id = item.data(Qt.UserRole)
                if cust_id in selected_ids:
                    item.setSelected(True)
        else:
            # Для нового проекта выбираем первого инженера и первого заказчика по умолчанию (если есть)
            if self.engineer_combo.count() > 1:  # первый элемент -- "-- Не выбрано --"
                self.engineer_combo.setCurrentIndex(1)
            if self.customers_list.count() > 0:
                self.customers_list.item(0).setSelected(True)

    def _manage_engineers(self):
        """Открывает диалог управления кадастровыми инженерами."""
        from .customer_engineer_dialog import CustomerEngineerDialog
        dlg = CustomerEngineerDialog(self, self.session, mode='engineer')
        if dlg.exec():
            # После закрытия диалога перезагружаем список инженеров
            self._reload_engineers()

    def _manage_customers(self):
        """Открывает диалог управления заказчиками."""
        from .customer_engineer_dialog import CustomerEngineerDialog
        dlg = CustomerEngineerDialog(self, self.session, mode='customer')
        if dlg.exec():
            # После закрытия перезагружаем список заказчиков
            self._reload_customers()

    def _reload_engineers(self):
        """Перезагружает список инженеров из БД."""
        current_id = self.engineer_combo.currentData()
        engineers = self.session.query(CadastralEngineer).all()
        self.engineer_combo.clear()
        self.engineer_combo.addItem("-- Не выбрано --", None)
        for eng in engineers:
            name = f"{eng.family_name} {eng.first_name} {eng.patronymic or ''}".strip()
            self.engineer_combo.addItem(f"{name} (атт. {eng.attestation_number})", eng.id)
        if current_id:
            idx = self.engineer_combo.findData(current_id)
            if idx >= 0:
                self.engineer_combo.setCurrentIndex(idx)

    def _reload_customers(self):
        """Перезагружает список заказчиков, сохраняя выделение."""
        selected_ids = [self.customers_list.item(i).data(Qt.UserRole)
                        for i in range(self.customers_list.count())
                        if self.customers_list.item(i).isSelected()]
        customers = self.session.query(Customer).all()
        self.customers_list.clear()
        for cust in customers:
            if cust.customer_type == 'person':
                name = f"{cust.family_name} {cust.first_name} {cust.patronymic or ''}".strip()
                display = f"{name} (физлицо)"
            elif cust.customer_type == 'organization':
                display = f"{cust.full_name} (юрлицо)"
            elif cust.customer_type == 'governance':
                display = f"{cust.full_name} (орган власти)"
            else:
                display = f"{cust.full_name or ''} (иностранное)"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, cust.id)
            self.customers_list.addItem(item)
            if cust.id in selected_ids:
                item.setSelected(True)

    def validate_and_accept(self):
        """Проверяет заполнение обязательных полей и закрывает диалог с успехом."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Предупреждение", "Название проекта обязательно.")
            return

        engineer_id = self.engineer_combo.currentData()
        # Инженер может быть не выбран, но в демо-данных он будет

        # Собираем ID выбранных заказчиков
        selected_customers = []
        for i in range(self.customers_list.count()):
            item = self.customers_list.item(i)
            if item.isSelected():
                cust_id = item.data(Qt.UserRole)
                selected_customers.append(cust_id)

        self._data = {
            'name': name,
            'description': self.description_edit.toPlainText().strip() or None,
            'engineer_id': engineer_id,
            'customer_ids': selected_customers
        }
        self.accept()

    def get_data(self):
        """
        Возвращает данные, введённые в диалоге.

        Returns:
            Словарь с ключами: name, description, engineer_id, customer_ids.
        """
        return self._data