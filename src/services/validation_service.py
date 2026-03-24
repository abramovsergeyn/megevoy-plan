# src/services/validation_service.py
# Сервис для валидации XML-документов межевого плана по XSD-схеме.
# Использует библиотеку lxml для загрузки схемы и выполнения проверки.

from lxml import etree
from typing import Tuple, List

from ..utils.config import MP_SCHEMA  # путь к главной схеме MP_v09.xsd
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ValidationService:
    """
    Сервис валидации XML-документов.
    Позволяет проверить сгенерированный XML-файл на соответствие схеме Росреестра.
    """

    def __init__(self):
        """
        Инициализация: загружает XSD-схему из файла.
        В случае ошибки загрузки схемы логирует исключение и сохраняет None.
        """
        self.schema = None
        try:
            with open(MP_SCHEMA, 'rb') as f:
                schema_doc = etree.parse(f)
            self.schema = etree.XMLSchema(schema_doc)
            logger.info(f"Схема {MP_SCHEMA} успешно загружена")
        except Exception as e:
            logger.exception(f"Не удалось загрузить схему {MP_SCHEMA}: {e}")

    def validate_xml(self, xml_file: str) -> Tuple[bool, List[str]]:
        """
        Проверяет XML-файл на соответствие загруженной XSD-схеме.

        Args:
            xml_file: Путь к XML-файлу для проверки.

        Returns:
            Кортеж (успех, список_ошибок):
                - успех: True, если файл соответствует схеме, иначе False.
                - список_ошибок: пустой список при успехе, иначе список строк с описанием ошибок.
        """
        if self.schema is None:
            logger.error("Схема не загружена, валидация невозможна")
            return False, ["Схема не загружена"]

        try:
            with open(xml_file, 'rb') as f:
                doc = etree.parse(f)

            if self.schema.validate(doc):
                logger.info(f"XML {xml_file} успешно прошёл валидацию")
                return True, []
            else:
                # Собираем все ошибки из лога схемы
                errors = [str(error) for error in self.schema.error_log]
                logger.error(f"Ошибки валидации XML {xml_file}: {errors}")
                return False, errors

        except etree.XMLSyntaxError as e:
            logger.exception(f"Синтаксическая ошибка в XML {xml_file}")
            return False, [f"Синтаксическая ошибка XML: {e}"]
        except Exception as e:
            logger.exception(f"Ошибка при валидации XML {xml_file}")
            return False, [str(e)]

    def validate_project(self, project) -> Tuple[bool, List[str]]:
        """
        (Опционально) Логическая проверка проекта перед генерацией XML.
        Проверяет обязательные поля, корректность кадастровых номеров,
        замкнутость контуров и т.п. Может быть расширена по мере необходимости.

        Args:
            project: Объект Project (модель SQLAlchemy).

        Returns:
            Кортеж (успех, список_предупреждений/ошибок).
        """
        errors = []
        # Проверка наличия кадастрового инженера
        if not project.engineer:
            errors.append("Отсутствует кадастровый инженер")
        # Проверка наличия хотя бы одного участка
        if not project.parcels:
            errors.append("Проект не содержит участков")
        # Для каждого участка можно проверить координаты и т.д.
        for parcel in project.parcels:
            if not parcel.points and not parcel.contours:
                errors.append(f"Участок {parcel.id} не имеет ни точек, ни контуров")
            # Можно добавить проверку замкнутости и пр.
        if errors:
            logger.warning(f"Логические ошибки проекта: {errors}")
            return False, errors
        return True, []