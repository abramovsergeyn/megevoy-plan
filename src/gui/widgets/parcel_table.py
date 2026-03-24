# src/gui/widgets/parcel_table.py
# Модель таблицы для отображения списка земельных участков в главном окне.
# Реализует интерфейс QAbstractTableModel для связи с QTreeView/QTableView.

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from ...models import Parcel, LandCategory
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ParcelTableModel(QAbstractTableModel):
    """
    Модель таблицы для отображения земельных участков текущего проекта.
    Колонки:
    0 - Кадастровый номер
    1 - Статус
    2 - Категория земель
    3 - Площадь (кв.м)
    4 - Кадастровый квартал
    """

    # Заголовки колонок
    HEADERS = ["Кадастровый номер", "Статус", "Категория земель", "Площадь (кв.м)", "Кадастровый квартал"]

    def __init__(self, parcels=None):
        """
        Инициализация модели.

        Args:
            parcels: Список объектов Parcel (может быть пустым).
        """
        super().__init__()
        self.parcels = parcels if parcels is not None else []

    def rowCount(self, parent=QModelIndex()) -> int:
        """
        Возвращает количество строк (участков).
        """
        return len(self.parcels)

    def columnCount(self, parent=QModelIndex()) -> int:
        """
        Возвращает количество колонок.
        """
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """
        Возвращает данные для ячейки по заданной роли.
        """
        if not index.isValid():
            return None

        parcel = self.parcels[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            # Текст для отображения
            if col == 0:
                return parcel.cadastral_number or ""
            elif col == 1:
                return parcel.status.value if parcel.status else ""
            elif col == 2:
                # Получаем наименование категории по коду
                if parcel.land_category_code:
                    # Здесь можно загрузить из сессии, но в модели нет доступа к БД.
                    # Лучше хранить имя категории в самом участке или получать через связь.
                    # В упрощённом варианте вернём код.
                    return parcel.land_category_code
                return ""
            elif col == 3:
                return f"{parcel.area:.2f}" if parcel.area is not None else ""
            elif col == 4:
                return parcel.cadastral_block or ""

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Цвет фона для строк (например, в зависимости от статуса)
            if parcel.status:
                if parcel.status.value == "образуемый":
                    return QColor(230, 255, 230)  # светло-зелёный
                elif parcel.status.value == "измененный":
                    return QColor(255, 255, 200)  # светло-жёлтый
                elif parcel.status.value == "смежный":
                    return QColor(230, 230, 255)  # светло-синий
                # остальные – без фона

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Возвращает заголовки колонок.
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Определяет флаги элемента (нередактируемый, выбираемый).
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def set_parcels(self, parcels):
        """
        Обновляет список участков и сигнализирует об изменении модели.

        Args:
            parcels: Новый список участков.
        """
        self.beginResetModel()
        self.parcels = parcels
        self.endResetModel()
        logger.debug(f"Модель таблицы обновлена: {len(parcels)} участков")

    def get_parcel(self, row: int) -> Parcel:
        """
        Возвращает участок по индексу строки.

        Args:
            row: Номер строки.

        Returns:
            Объект Parcel.
        """
        if 0 <= row < len(self.parcels):
            return self.parcels[row]
        raise IndexError(f"Строка {row} вне диапазона")