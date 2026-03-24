# src/services/import_service.py
# Сервис для импорта координат из внешних форматов (CSV, KML).
# Поддерживается импорт списка точек, которые затем могут быть использованы
# для создания характерных точек земельного участка.

import csv
from typing import List, Tuple, Optional
from lxml import etree

from ..utils.logger import get_logger

logger = get_logger(__name__)


def import_coordinates_from_csv(
    filepath: str,
    delimiter: str = ',',
    skip_header: bool = True,
    x_column: int = 0,
    y_column: int = 1
) -> List[Tuple[float, float]]:
    """
    Импорт координат из CSV-файла.

    Args:
        filepath: Путь к CSV-файлу.
        delimiter: Разделитель полей (по умолчанию запятая).
        skip_header: Пропускать ли первую строку (заголовок).
        x_column: Индекс столбца с координатой X (начиная с 0).
        y_column: Индекс столбца с координатой Y.

    Returns:
        Список кортежей (x, y) в порядке следования в файле.

    Raises:
        ValueError: Если файл не содержит достаточного количества столбцов
                    или координаты не могут быть преобразованы в числа.
        IOError: При ошибках чтения файла.
    """
    coords = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=delimiter)
            lines = list(reader)
    except Exception as e:
        logger.exception(f"Ошибка открытия файла {filepath}")
        raise IOError(f"Не удалось прочитать файл: {e}")

    if not lines:
        logger.warning(f"Файл {filepath} пуст")
        return []

    start_row = 1 if skip_header else 0
    for i, row in enumerate(lines[start_row:], start=start_row+1):
        if len(row) <= max(x_column, y_column):
            logger.error(f"Строка {i} содержит недостаточно столбцов: {row}")
            raise ValueError(f"В строке {i} недостаточно столбцов (ожидается минимум {max(x_column, y_column)+1})")

        try:
            x = float(row[x_column].strip())
            y = float(row[y_column].strip())
            coords.append((x, y))
        except ValueError as e:
            logger.error(f"Строка {i}: нечисловое значение координат: {row[x_column]}, {row[y_column]}")
            raise ValueError(f"Ошибка преобразования координат в строке {i}: {e}")

    logger.info(f"Импортировано {len(coords)} точек из CSV {filepath}")
    return coords


def _parse_coordinate_string(coord_str: str) -> List[Tuple[float, float]]:
    """
    Вспомогательная функция для разбора строки координат из KML.
    Строка обычно содержит тройки чисел, разделённые пробелами или переводами строк:
    "lon1,lat1,alt1 lon2,lat2,alt2 ..." или с переносами.
    Возвращает список (x, y) игнорируя высоту.
    """
    coords = []
    # Разделяем по пробелам и переводам строк
    parts = coord_str.strip().replace('\n', ' ').split()
    for part in parts:
        # Каждая часть должна содержать три числа через запятую
        values = part.split(',')
        if len(values) >= 2:
            try:
                lon = float(values[0].strip())
                lat = float(values[1].strip())
                # В KML обычно порядок: долгота, широта. Интерпретируем как (x, y)
                coords.append((lon, lat))
            except ValueError:
                logger.warning(f"Невозможно преобразовать координаты: {part}")
                continue
    return coords


def import_from_kml(filepath: str) -> List[Tuple[float, float]]:
    """
    Импорт координат из KML-файла.
    Извлекает координаты первого найденного полигона (тег <Polygon>/<outerBoundaryIs>/<LinearRing>/<coordinates>).
    Поддерживается KML 2.2 (Google Earth).

    Args:
        filepath: Путь к KML-файлу.

    Returns:
        Список кортежей (x, y) в порядке обхода контура.

    Raises:
        ValueError: Если файл не содержит полигона или координат.
        IOError: При ошибках чтения файла.
    """
    try:
        tree = etree.parse(filepath)
    except Exception as e:
        logger.exception(f"Ошибка парсинга KML {filepath}")
        raise IOError(f"Не удалось разобрать KML-файл: {e}")

    # Пространство имён KML 2.2
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    # Ищем первый элемент <coordinates> внутри полигона
    # Можно искать по любому пути, содержащему coordinates
    coords_elem = tree.find(".//kml:coordinates", namespaces=ns)
    if coords_elem is None or not coords_elem.text:
        logger.error(f"В файле {filepath} не найдены координаты полигона")
        raise ValueError("KML не содержит координат полигона")

    coord_text = coords_elem.text
    coords = _parse_coordinate_string(coord_text)

    if not coords:
        raise ValueError("Не удалось извлечь ни одной координаты из KML")

    logger.info(f"Импортировано {len(coords)} точек из KML {filepath}")
    return coords