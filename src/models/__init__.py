# src/models/__init__.py
# Файл инициализации пакета models.
# Экспортирует все модели данных, чтобы их можно было импортировать напрямую из пакета,
# например: from src.models import Project, CadastralEngineer, ParcelStatus и т.д.

from .base import Base
from .dictionaries import (
    LandCategory,
    AllowedUse,
    Region,
    GeopointMethod,
    EncumbranceType,
    DocumentType
)
from .project import Project
from .engineer import CadastralEngineer
from .customer import Customer
from .parcel import Parcel, ParcelStatus  # обязательно экспортируем и класс, и перечисление
from .point import CharacteristicPoint
from .contour import Contour
from .adjacency import Adjacency
from .encumbrance import ParcelPart

# Список всех экспортируемых имён (опционально, для удобства)
__all__ = [
    'Base',
    'LandCategory',
    'AllowedUse',
    'Region',
    'GeopointMethod',
    'EncumbranceType',
    'DocumentType',
    'Project',
    'CadastralEngineer',
    'Customer',
    'Parcel',
    'ParcelStatus',
    'CharacteristicPoint',
    'Contour',
    'Adjacency',
    'ParcelPart',
]