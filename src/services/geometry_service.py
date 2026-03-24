# src/services/geometry_service.py
# Сервис для выполнения геометрических операций с координатами земельных участков.
# Использует библиотеку Shapely для создания полигонов, проверки топологии,
# вычисления площади и обнаружения пересечений.

from typing import List, Tuple, Optional
import shapely.geometry as sg
import shapely.validation as sv
from shapely.ops import unary_union
from ..utils.logger import get_logger

logger = get_logger(__name__)


def polygon_from_coords(coords: List[Tuple[float, float]]) -> sg.Polygon:
    """
    Создаёт полигон Shapely из списка координат (x, y).
    Автоматически замыкает контур, если первая и последняя точки различаются.

    Args:
        coords: Список кортежей (x, y) в порядке обхода контура.

    Returns:
        Объект shapely.geometry.Polygon.

    Raises:
        ValueError: Если передано менее 3 точек (невозможно построить полигон).
    """
    if len(coords) < 3:
        raise ValueError("Для построения полигона необходимо минимум 3 точки")

    # Если контур не замкнут, добавляем первую точку в конец
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
        logger.debug("Контур замкнут автоматически")

    return sg.Polygon(coords)


def calculate_area(coords: List[Tuple[float, float]]) -> float:
    """
    Вычисляет площадь полигона в квадратных метрах.

    Args:
        coords: Список координат (x, y) характерных точек в порядке обхода.

    Returns:
        Площадь полигона (положительное число).
    """
    poly = polygon_from_coords(coords)
    area = poly.area
    logger.debug(f"Вычислена площадь: {area:.2f} кв. м")
    return area


def is_closed(coords: List[Tuple[float, float]], tolerance: float = 0.01) -> bool:
    """
    Проверяет замкнутость контура: расстояние между первой и последней точкой
    не превышает заданного допуска.

    Args:
        coords: Список координат (x, y).
        tolerance: Допустимое расстояние (в метрах) для признания контура замкнутым.

    Returns:
        True, если контур замкнут, иначе False.
    """
    if len(coords) < 2:
        return False

    first = coords[0]
    last = coords[-1]
    dist = ((first[0] - last[0]) ** 2 + (first[1] - last[1]) ** 2) ** 0.5
    result = dist <= tolerance
    logger.debug(f"Проверка замкнутости: расстояние {dist:.3f} м, результат {result}")
    return result


def is_self_intersecting(coords: List[Tuple[float, float]]) -> bool:
    """
    Проверяет наличие самопересечений у полигона.

    Args:
        coords: Список координат (x, y).

    Returns:
        True, если полигон самопересекается (невалидный), иначе False.
    """
    poly = polygon_from_coords(coords)
    valid = poly.is_valid
    if not valid:
        logger.debug("Обнаружены самопересечения полигона")
    return not valid


def check_intersections(parcels_coords: List[List[Tuple[float, float]]]) -> List[Tuple[int, int]]:
    """
    Проверяет пересечения между несколькими участками.

    Args:
        parcels_coords: Список списков координат для каждого участка.

    Returns:
        Список пар индексов (i, j), где i < j, указывающий на пересекающиеся участки.
    """
    polys = [polygon_from_coords(c) for c in parcels_coords]
    intersections = []
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            if polys[i].intersects(polys[j]):
                logger.debug(f"Участки {i} и {j} пересекаются")
                intersections.append((i, j))
    return intersections


def compute_inaccuracy(
    method: str,
    category: Optional[str] = None,
    equipment_data: Optional[dict] = None
) -> float:
    """
    Вычисляет среднюю квадратическую погрешность (СКП) определения координат
    характерной точки в зависимости от метода измерений и категории земель.

    Args:
        method: Код метода определения координат (из справочника dGeopointOpred).
        category: Код категории земель (влияет на допустимую погрешность).
        equipment_data: Словарь с характеристиками оборудования (например, точность прибора).

    Returns:
        Значение СКП в метрах (положительное число).

    Примечание:
        В данной упрощённой реализации возвращаются нормативные значения
        для разных категорий земель согласно приказу Росреестра № П/0393.
        Для земель населённых пунктов – 0.10 м, для сельхозземель – 0.20 м,
        для промышленных земель – 0.50 м, для прочих – 0.30 м.
        При наличии equipment_data можно реализовать более точный расчёт.
    """
    # Базовая погрешность в зависимости от метода (условно)
    method_base = {
        '692001000000': 0.05,  # геодезический
        '692002000000': 0.20,  # фотограмметрический
        '692003000000': 0.30,  # картометрический
        '692005000000': 0.03,  # спутниковые измерения
        '692006000000': 0.10,  # аналитический
    }.get(method, 0.10)

    # Корректировка по категории земель (нормативные значения)
    category_factor = {
        '003002000000': 0.10,  # населённые пункты
        '003001000000': 0.20,  # сельхозземли
        '003003000000': 0.50,  # промышленность
    }.get(category, 0.30)

    # Итоговая погрешность (как максимум из двух, либо комбинация)
    # В реальности СКП зависит от класса точности оборудования и методики.
    result = max(method_base, category_factor)
    logger.debug(f"Вычислена СКП: {result:.2f} м (метод={method}, категория={category})")
    return result


def buffer_polygon(coords: List[Tuple[float, float]], distance: float) -> sg.Polygon:
    """
    Строит буферную зону вокруг полигона на заданное расстояние.

    Args:
        coords: Список координат (x, y) исходного полигона.
        distance: Радиус буфера в метрах.

    Returns:
        Полигон, представляющий буферную зону.
    """
    poly = polygon_from_coords(coords)
    buffered = poly.buffer(distance)
    logger.debug(f"Построена буферная зона на {distance} м")
    return buffered


def simplify_polygon(coords: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
    """
    Упрощает полигон с заданным допуском (алгоритм Дугласа-Пекера).

    Args:
        coords: Список координат (x, y).
        tolerance: Допуск упрощения в метрах.

    Returns:
        Упрощённый список координат.
    """
    poly = polygon_from_coords(coords)
    simplified = poly.simplify(tolerance, preserve_topology=True)
    # Преобразуем обратно в список кортежей
    if simplified.geom_type == 'Polygon':
        exterior = list(simplified.exterior.coords)
        return exterior[:-1]  # убираем замыкающую точку, если нужно
    else:
        logger.warning("Упрощение привело к мультиполигону или другому типу, возвращаем исходные координаты")
        return coords