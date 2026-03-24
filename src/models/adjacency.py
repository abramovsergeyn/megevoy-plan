# src/models/adjacency.py
# Модель смежного земельного участка.
# Хранит информацию о граничащих участках, их правообладателях и результате согласования границ.

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class Adjacency(Base):
    """
    Смежный земельный участок (соседний), граничащий с уточняемым или образуемым участком.
    Используется для формирования раздела согласования границ в межевом плане.
    """
    __tablename__ = 'adjacency'

    # Кадастровый номер смежного земельного участка (обязательное поле)
    # Формат: AA:BB:CCCCCC:K (как и для основного участка)
    adjacent_cadastral_number = Column(String(40), nullable=False,
                                       comment='Кадастровый номер смежного участка')

    # Сведения о правообладателе смежного участка (ФИО / наименование, адрес и т.п.)
    # Заполняется в соответствии с требованиями к акту согласования
    owner_info = Column(String(4000), nullable=True,
                        comment='Сведения о правообладателе смежного участка')

    # Результат согласования границы с данным смежным участком:
    # True – согласовано, False – имеются возражения (спор), None – согласование не проводилось
    согласование_status = Column(Boolean, nullable=True,
                                  comment='Статус согласования: True - согласовано, False - спорно, NULL - нет данных')

    # Внешний ключ к основному земельному участку (тому, для которого заполняется смежный)
    parcel_id = Column(Integer, ForeignKey('parcel.id'), nullable=False,
                       comment='ID основного участка, к которому относится смежный')

    # Связь с основным участком (обратная сторона отношения из Parcel)
    parcel = relationship('Parcel', back_populates='adjacencies', lazy='selectin')

    def __repr__(self):
        status_str = {
            True: 'согласовано',
            False: 'спорно',
            None: 'не определено'
        }.get(self.согласование_status, 'не определено')
        return (f"<Adjacency(id={self.id}, "
                f"adjacent='{self.adjacent_cadastral_number}', "
                f"status='{status_str}')>")