# src/gui/dialogs/customer_engineer_dialog.py
# Диалог для управления справочниками кадастровых инженеров и заказчиков.
# Содержит две вкладки (или один режим, выбираемый при создании) для просмотра,
# добавления, редактирования и удаления записей.

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QTabWidget, QWidget, QInputDialog, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

from sqlalchemy.orm import Session

from ...models import CadastralEngineer, Customer
from ...utils.logger import get_logger
from datetime import date

logger = get_logger(__name__)


class CustomerEngineerDialog(QDialog):
    """
    Диалог для просмотра и редактирования списка кадастровых инженеров или заказчиков.
    Режим работы задаётся параметром mode: 'engineer' или 'customer'.
    """

    def __init__(self, parent, session: Session, mode: str = 'engineer'):
        """
        Инициализация диалога.

        Args:
            parent: Родительский виджет.
            session: Сессия SQLAlchemy.
            mode: Режим работы: 'engineer' – кадастровые инженеры,
                                 'customer' – заказчики.
        """
        super().__init__(parent)
        self.session = session
        self.mode = mode
        self.setWindowTitle("Кадастровые инженеры" if mode == 'engineer' else "Заказчики")
        self.resize(800, 500)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Создание интерфейса диалога."""
        main_layout = QVBoxLayout(self)

        # Таблица для отображения записей
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(self.table)

        # Панель кнопок
        button_layout = QHBoxLayout()

        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self._add_record)
        button_layout.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self._edit_record)
        button_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_record)
        button_layout.addWidget(self.btn_delete)

        button_layout.addStretch()

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)

        main_layout.addLayout(button_layout)

    def _load_data(self):
        """Загрузка данных из БД и заполнение таблицы."""
        if self.mode == 'engineer':
            self._load_engineers()
        else:
            self._load_customers()

    def _load_engineers(self):
        """Заполнение таблицы кадастровыми инженерами."""
        engineers = self.session.query(CadastralEngineer).order_by(CadastralEngineer.family_name).all()
        # Заголовки столбцов: ID, Фамилия, Имя, Отчество, СНИЛС, Аттестат, Телефон, СРО
        headers = ["ID", "Фамилия", "Имя", "Отчество", "СНИЛС", "Аттестат", "Телефон", "СРО"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(engineers))

        for row, eng in enumerate(engineers):
            self.table.setItem(row, 0, QTableWidgetItem(str(eng.id)))
            self.table.setItem(row, 1, QTableWidgetItem(eng.family_name))
            self.table.setItem(row, 2, QTableWidgetItem(eng.first_name))
            self.table.setItem(row, 3, QTableWidgetItem(eng.patronymic or ""))
            self.table.setItem(row, 4, QTableWidgetItem(eng.snils))
            self.table.setItem(row, 5, QTableWidgetItem(eng.attestation_number))
            self.table.setItem(row, 6, QTableWidgetItem(eng.phone))
            self.table.setItem(row, 7, QTableWidgetItem(eng.sro_name))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # скрываем колонку ID (она для служебного использования)
        self.table.setColumnHidden(0, True)

    def _load_customers(self):
        """Заполнение таблицы заказчиками."""
        customers = self.session.query(Customer).order_by(Customer.id).all()
        # Заголовки: ID, Тип, Наименование (ФИО/Название), ИНН, Телефон, Email
        headers = ["ID", "Тип", "Наименование", "ИНН", "Телефон", "Email"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(customers))

        for row, cust in enumerate(customers):
            # Формируем отображаемое наименование
            if cust.customer_type == 'person':
                name = f"{cust.family_name or ''} {cust.first_name or ''} {cust.patronymic or ''}".strip()
                type_display = "Физлицо"
            elif cust.customer_type == 'organization':
                name = cust.full_name or ''
                type_display = "Юрлицо"
            elif cust.customer_type == 'governance':
                name = cust.full_name or ''
                type_display = "Орган власти"
            else:
                name = cust.full_name or ''
                type_display = "Иностранное"

            self.table.setItem(row, 0, QTableWidgetItem(str(cust.id)))
            self.table.setItem(row, 1, QTableWidgetItem(type_display))
            self.table.setItem(row, 2, QTableWidgetItem(name))
            self.table.setItem(row, 3, QTableWidgetItem(cust.inn or cust.inn_person or ""))
            self.table.setItem(row, 4, QTableWidgetItem(cust.phone or ""))
            self.table.setItem(row, 5, QTableWidgetItem(cust.email or ""))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)  # скрываем ID

    def _add_record(self):
        """Добавление новой записи."""
        if self.mode == 'engineer':
            self._add_engineer()
        else:
            self._add_customer()

    def _add_engineer(self):
        """
        Добавление кадастрового инженера.
        В реальном приложении здесь должен открываться диалог с формой,
        содержащей все поля модели CadastralEngineer.
        Для демонстрации используем упрощённый ввод через QInputDialog.
        """
        # Упрощённо: запрашиваем фамилию, имя, СНИЛС
        family_name, ok = QInputDialog.getText(self, "Новый инженер", "Фамилия:")
        if not ok or not family_name:
            return
        first_name, ok = QInputDialog.getText(self, "Новый инженер", "Имя:")
        if not ok or not first_name:
            return
        snils, ok = QInputDialog.getText(self, "Новый инженер", "СНИЛС (11 цифр):")
        if not ok or not snils:
            return

        # Создаём объект и сохраняем
        engineer = CadastralEngineer(
            family_name=family_name,
            first_name=first_name,
            snils=snils,
            attestation_number="",   # заглушка
            date_entering=date.today(),
            phone="",
            address="",
            sro_name=""
        )
        self.session.add(engineer)
        self.session.commit()
        logger.info(f"Добавлен инженер: {family_name} {first_name}")
        self._load_engineers()

    def _add_customer(self):
        """
        Добавление заказчика.
        Аналогично упрощённо.
        """
        # Запрашиваем тип
        type_map = {
            "Физическое лицо": "person",
            "Юридическое лицо": "organization",
            "Орган власти": "governance",
            "Иностранное юрлицо": "foreign"
        }
        type_display, ok = QInputDialog.getItem(
            self, "Тип заказчика", "Выберите тип:",
            list(type_map.keys()), 0, False
        )
        if not ok:
            return
        cust_type = type_map[type_display]

        # Запрашиваем наименование/ФИО
        name, ok = QInputDialog.getText(self, "Новый заказчик", "Наименование / ФИО:")
        if not ok or not name:
            return

        # Создаём объект
        customer = Customer(customer_type=cust_type)
        if cust_type == 'person':
            parts = name.split(maxsplit=2)
            customer.family_name = parts[0] if len(parts) > 0 else ""
            customer.first_name = parts[1] if len(parts) > 1 else ""
            customer.patronymic = parts[2] if len(parts) > 2 else ""
        else:
            customer.full_name = name

        self.session.add(customer)
        self.session.commit()
        logger.info(f"Добавлен заказчик: {name}")
        self._load_customers()

    def _edit_record(self):
        """Редактирование выбранной записи."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите запись для редактирования")
            return

        # Получаем ID из скрытой колонки
        id_item = self.table.item(current_row, 0)
        if not id_item:
            return
        record_id = int(id_item.text())

        if self.mode == 'engineer':
            self._edit_engineer(record_id)
        else:
            self._edit_customer(record_id)

    def _edit_engineer(self, engineer_id: int):
        """Редактирование кадастрового инженера."""
        engineer = self.session.get(CadastralEngineer, engineer_id)
        if not engineer:
            return

        # Упрощённо: позволяем изменить телефон
        new_phone, ok = QInputDialog.getText(
            self, "Редактирование инженера",
            "Телефон:", text=engineer.phone or ""
        )
        if ok:
            engineer.phone = new_phone
            self.session.commit()
            self._load_engineers()

    def _edit_customer(self, customer_id: int):
        """Редактирование заказчика."""
        customer = self.session.get(Customer, customer_id)
        if not customer:
            return

        # Упрощённо: позволяем изменить телефон
        new_phone, ok = QInputDialog.getText(
            self, "Редактирование заказчика",
            "Телефон:", text=customer.phone or ""
        )
        if ok:
            customer.phone = new_phone
            self.session.commit()
            self._load_customers()

    def _delete_record(self):
        """Удаление выбранной записи с подтверждением."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите запись для удаления")
            return

        id_item = self.table.item(current_row, 0)
        if not id_item:
            return
        record_id = int(id_item.text())

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы действительно хотите удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if self.mode == 'engineer':
            engineer = self.session.get(CadastralEngineer, record_id)
            if engineer:
                self.session.delete(engineer)
                self.session.commit()
                logger.info(f"Удалён инженер ID {record_id}")
        else:
            customer = self.session.get(Customer, record_id)
            if customer:
                self.session.delete(customer)
                self.session.commit()
                logger.info(f"Удалён заказчик ID {record_id}")

        self._load_data()  # обновить таблицу