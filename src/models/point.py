# src/models/point.py
# Модель характерной точки границы земельного участка или контура многоконтурного участка.

from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class CharacteristicPoint(Base):
    """
    Характерная точка границы земельного участка или контура.
    Содержит координаты, погрешность, метод определения и дополнительные атрибуты.
    Может быть привязана непосредственно к участку (если участок не многоконтурный)
    либо к контуру (для многоконтурных участков).
    """
    __tablename__ = 'characteristicpoint'

    point_number = Column(Integer, nullable=False, comment='Порядковый номер точки')
    x = Column(Float, nullable=False, comment='Координата X (метры)')
    y = Column(Float, nullable=False, comment='Координата Y (метры)')
    delta = Column(Float, nullable=True, comment='СКП положения точки (метры)')
    method_code = Column(String(12), ForeignKey('geopoint_methods.code'), nullable=True,
                         comment='Код метода определения координат')
    formula = Column(String(4000), nullable=True, comment='Формула определения координат')
    point_pref = Column(String(30), nullable=True, comment='Префикс номера точки')
    description = Column(String(120), nullable=True, comment='Описание закрепления точки')

    parcel_id = Column(Integer, ForeignKey('parcel.id'), nullable=True, comment='ID участка (если не многоконтурный)')
    contour_id = Column(Integer, ForeignKey('contour.id'), nullable=True, comment='ID контура (для многоконтурных)')

    # Связи (должны совпадать с back_populates в родительских моделях)
    parcel = relationship('Parcel', back_populates='points')
    contour = relationship('Contour', back_populates='points')

    def __repr__(self):
        return (f"<CharacteristicPoint(id={self.id}, num={self.point_number}, "
                f"x={self.x:.2f}, y={self.y:.2f}, delta={self.delta})>")