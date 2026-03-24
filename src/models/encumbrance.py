# src/models/encumbrance.py
# Модель части земельного участка (обременения).
# Хранит информацию о частях участка, возникающих в связи с ограничениями прав.

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class ParcelPart(Base):
    """
    Часть земельного участка, как правило, связанная с ограничением (обременением).
    """
    __tablename__ = 'parcel_part'

    account_number = Column(String(50), nullable=False, comment='Учётный номер части')
    area = Column(Float, nullable=False, comment='Площадь части (кв. м)')
    area_inaccuracy = Column(Float, nullable=True, comment='Погрешность площади части (кв. м)')
    area_formula = Column(String(4000), nullable=True, comment='Формула вычисления площади части')
    restriction_type_code = Column(String(12), ForeignKey('encumbrance_types.code'), nullable=False,
                                   comment='Код вида ограничения/обременения')
    restriction_name = Column(String(4000), nullable=True, comment='Содержание ограничения (обременения)')
    reg_numb_border = Column(String(50), nullable=True, comment='Реестровый номер границы зоны')
    cadastral_number_restriction = Column(String(40), nullable=True,
                                          comment='Кадастровый номер ЗУ, в пользу которого установлен сервитут')
    parcel_id = Column(Integer, ForeignKey('parcel.id'), nullable=False, comment='ID земельного участка')
    parcel = relationship('Parcel', back_populates='parts', lazy='selectin')

    # Временное отключение связи с точками, так как столбец part_id не существует
    # points = relationship(
    #     'CharacteristicPoint',
    #     primaryjoin='and_(CharacteristicPoint.part_id==ParcelPart.id)',
    #     cascade='all, delete-orphan',
    #     lazy='selectin',
    #     viewonly=True
    # )

    def __repr__(self):
        return (f"<ParcelPart(id={self.id}, account='{self.account_number}', "
                f"area={self.area:.2f}, type='{self.restriction_type_code}')>")