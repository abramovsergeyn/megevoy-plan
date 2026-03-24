# src/services/export_service.py
# Сервис для экспорта данных проекта в различные форматы.
# Основной функционал: экспорт межевого плана в XML (согласно схеме MP_v09.xsd).
# Дополнительно: экспорт координат участков в CSV.

from typing import List, Tuple, Optional
from ..models import Project, Parcel, CharacteristicPoint
from .xml_service import XMLGenerator
from ..utils.logger import get_logger
import csv
import os

logger = get_logger(__name__)


class ExportService:
    """
    Сервис экспорта данных проекта.
    Предоставляет методы для сохранения проекта в XML-формат межевого плана,
    а также для выгрузки координат характерных точек в CSV.
    """

    def __init__(self, project: Project):
        """
        Инициализация сервиса с проектом.

        Args:
            project: Объект проекта, данные которого будут экспортироваться.
        """
        self.project = project

    def export_to_xml(self, filepath: str) -> bool:
        """
        Экспортирует проект в XML-файл межевого плана.

        Args:
            filepath: Полный путь к сохраняемому XML-файлу (включая имя и расширение).

        Returns:
            True, если экспорт выполнен успешно, иначе False.
        """
        try:
            # Создаём генератор XML на основе текущего проекта
            generator = XMLGenerator(self.project)
            # Генерируем и сохраняем XML
            generator.save(filepath)
            logger.info(f"Проект «{self.project.name}» успешно экспортирован в XML: {filepath}")
            return True
        except Exception as e:
            logger.exception(f"Ошибка при экспорте проекта в XML: {e}")
            return False

    def export_coordinates_to_csv(
        self,
        filepath: str,
        parcels: Optional[List[Parcel]] = None,
        delimiter: str = ',',
        include_headers: bool = True
    ) -> bool:
        """
        Экспортирует координаты характерных точек указанных участков в CSV-файл.
        Формат строки: номер_точки, X, Y, СКП, метод (опционально).

        Args:
            filepath: Путь для сохранения CSV-файла.
            parcels: Список участков для экспорта. Если None, экспортируются все участки проекта.
            delimiter: Разделитель полей (по умолчанию запятая).
            include_headers: Включать ли заголовок в первую строку.

        Returns:
            True, если экспорт выполнен успешно, иначе False.
        """
        try:
            if parcels is None:
                parcels = self.project.parcels

            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=delimiter)

                if include_headers:
                    writer.writerow(['point_number', 'x', 'y', 'delta', 'method_code', 'parcel_id'])

                for parcel in parcels:
                    for point in parcel.points:
                        writer.writerow([
                            point.point_number,
                            f"{point.x:.2f}",
                            f"{point.y:.2f}",
                            f"{point.delta:.2f}" if point.delta else '',
                            point.method_code or '',
                            parcel.id
                        ])
                    # Для многоконтурных участков точки хранятся в контурах, поэтому нужно добавить и их
                    for contour in parcel.contours:
                        for point in contour.points:
                            writer.writerow([
                                point.point_number,
                                f"{point.x:.2f}",
                                f"{point.y:.2f}",
                                f"{point.delta:.2f}" if point.delta else '',
                                point.method_code or '',
                                parcel.id
                            ])

            logger.info(f"Координаты экспортированы в CSV: {filepath}")
            return True
        except Exception as e:
            logger.exception(f"Ошибка при экспорте координат в CSV: {e}")
            return False

    def export_project_package(self, base_filename: str) -> bool:
        """
        Экспортирует полный пакет межевого плана:
        - XML-документ
        - (в будущем) PDF-чертежи
        - (в будущем) ZIP-архив

        Args:
            base_filename: Базовое имя файлов без расширения (например, "MP_123").

        Returns:
            True, если все файлы созданы успешно.
        """
        # На данный момент реализован только XML
        xml_path = f"{base_filename}.xml"
        return self.export_to_xml(xml_path)