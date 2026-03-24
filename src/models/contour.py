# src/models/contour.py
# Модель контура многоконтурного земельного участка.
# Каждый контур представляет собой замкнутый полигон, имеющий собственную площадь
# и список характерных точек. Многоконтурный участок состоит из одного или нескольких таких контуров.

from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Contour(Base):
    """
    Контур многоконтурного земельного участка.
    Содержит площадь и список характерных точек, образующих замкнутый контур.
    """
    __tablename__ = 'contour'

    # Учётный (порядковый) номер контура в пределах многоконтурного участка.
    # Соответствует атрибуту NumberRecord или Number в XML (в зависимости от контекста).
    contour_number = Column(Integer, nullable=False, comment='Порядковый номер контура в составе участка')

    # Площадь контура в квадратных метрах.
    # В отличие от площади участка (целое число), площадь контура может быть дробной (до 0.01 кв. м).
    area = Column(Float, nullable=False, comment='Площадь контура (кв. м)')

    # Погрешность определения площади контура (опционально).
    area_inaccuracy = Column(Float, nullable=True, comment='Погрешность площади контура (кв. м)')

    # Формула, использованная для вычисления площади контура (опционально).
    area_formula = Column(String(4000), nullable=True, comment='Формула вычисления площади контура')

    # Внешний ключ к родительскому земельному участку.
    parcel_id = Column(Integer, ForeignKey('parcel.id'), nullable=False, comment='ID многоконтурного участка')

    # Связь с родительским участком (обратная сторона отношения из Parcel).
    parcel = relationship('Parcel', back_populates='contours', lazy='selectin')

    # Список характерных точек, принадлежащих данному контуру.
    # Точки упорядочиваются по point_number для обеспечения правильного порядка обхода.
    points = relationship(
        'CharacteristicPoint',
        back_populates='contour',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='CharacteristicPoint.point_number'
    )

    def __repr__(self):
        return f"<Contour(id={self.id}, number={self.contour_number}, area={self.area:.2f})>"