# src/models/parcel.py
# Модель земельного участка в проекте межевания.
# Содержит все сведения, необходимые для формирования разделов межевого плана,
# касающихся земельных участков (образуемых, изменяемых, существующих, смежных).

import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class ParcelStatus(enum.Enum):
    """
    Статус земельного участка в рамках кадастровых работ.
    Соответствует типам, используемым в XML:
    - NEW: образуемый участок (NewParcel)
    - CHANGED: изменённый участок (ChangeParcel)
    - EXISTING: существующий участок (при уточнении границ)
    - ADJACENT: смежный участок (SpecifyRelatedParcel)
    """
    NEW = "образуемый"
    CHANGED = "измененный"
    EXISTING = "существующий"
    ADJACENT = "смежный"


class Parcel(Base):
    """
    Земельный участок (или его контур в случае многоконтурного участка).
    Для многоконтурных участков используется дополнительная таблица Contour.
    """
    __tablename__ = 'parcel'

    # Кадастровый номер участка (для существующих, изменённых, смежных)
    # Для образуемых участков может отсутствовать, тогда поле пустое.
    cadastral_number = Column(String(40), nullable=True, comment='Кадастровый номер (AA:BB:CCCCCC:K)')

    # Статус участка (см. ParcelStatus)
    status = Column(Enum(ParcelStatus), nullable=False, comment='Статус участка в проекте')

    # Площадь участка (в кв. м), вычисленная по координатам или заданная вручную
    area = Column(Float, nullable=True, comment='Площадь участка (кв. м)')

    # Погрешность определения площади (согласно требованиям к точности)
    area_inaccuracy = Column(Float, nullable=True, comment='Погрешность площади (кв. м)')

    # Формула, использованная для вычисления площади (если применимо)
    area_formula = Column(String(4000), nullable=True, comment='Формула вычисления площади')

    # Номер кадастрового квартала, в котором расположен участок (обязательно)
    cadastral_block = Column(String(13), nullable=False, comment='Номер кадастрового квартала (AA:BB:CCCCCC)')

    # Категория земель – ссылка на код из справочника LandCategory
    land_category_code = Column(String(12), ForeignKey('land_categories.code'), nullable=False,
                                comment='Код категории земель')

    # Вид разрешённого использования – либо код из справочника, либо текст
    permitted_use_code = Column(String(12), ForeignKey('allowed_uses.code'), nullable=True,
                                comment='Код вида разрешённого использования (по классификатору)')
    permitted_use_text = Column(String(4000), nullable=True,
                                comment='Вид разрешённого использования (текстовое описание)')

    # Адрес (местоположение) в структурированном виде согласно ФИАС
    address_text = Column(String(4000), nullable=True, comment='Адрес в неструктурированном виде (запасной вариант)')
    address_fias = Column(String(36), nullable=True, comment='Код ФИАС (GUID адреса)')
    address_region = Column(String(2), ForeignKey('regions.code'), nullable=False,
                            comment='Код региона (субъекта РФ)')
    address_district = Column(String(255), nullable=True, comment='Район')
    address_city = Column(String(255), nullable=True, comment='Муниципальное образование')
    address_urban_district = Column(String(255), nullable=True, comment='Городской район')
    address_soviet_village = Column(String(255), nullable=True, comment='Сельсовет')
    address_locality = Column(String(255), nullable=True, comment='Населённый пункт')
    address_street = Column(String(255), nullable=True, comment='Улица')
    address_level1 = Column(String(255), nullable=True, comment='Дом')
    address_level2 = Column(String(255), nullable=True, comment='Корпус')
    address_level3 = Column(String(255), nullable=True, comment='Строение')
    address_apartment = Column(String(255), nullable=True, comment='Квартира')
    address_other = Column(String(2500), nullable=True, comment='Дополнительные сведения о местоположении')
    address_note = Column(String(4000), nullable=True, comment='Неформализованное описание местоположения')
    address_or_location = Column(Integer, nullable=False, default=1,
                                 comment='1 – адрес, 0 – описание местоположения (атрибут AddressOrLocation)')

    # Внешний ключ к проекту
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False, comment='ID проекта')
    project = relationship('Project', back_populates='parcels', lazy='selectin')

    # Связь с характерными точками (один участок – много точек)
    # back_populates должно соответствовать имени атрибута в модели CharacteristicPoint (там 'parcel')
    points = relationship(
        'CharacteristicPoint',
        back_populates='parcel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    # Связь с контурами (для многоконтурных участков)
    contours = relationship(
        'Contour',
        back_populates='parcel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    # Связь с частями участка (обременениями)
    parts = relationship(
        'ParcelPart',
        back_populates='parcel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    # Связь со смежными участками
    adjacencies = relationship(
        'Adjacency',
        back_populates='parcel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    def __repr__(self):
        return f"<Parcel(id={self.id}, cadastral_number='{self.cadastral_number}', status='{self.status.value}')>"