# src/models/project.py
# Модель проекта межевания.
# Содержит основные сведения о проекте и связи с инженером, заказчиками, участками.
# Связь с документами пока отключена, так как модель DocumentBase не реализована.

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Project(Base):
    """
    Проект межевания земельного участка.
    Хранит общую информацию и связывает все сущности, относящиеся к одной кадастровой работе.
    """
    __tablename__ = 'project'

    # Название проекта (задается пользователем)
    name = Column(String(255), nullable=False, comment='Наименование проекта')

    # Описание / примечания к проекту (необязательно)
    description = Column(String, nullable=True, comment='Описание проекта')

    # Статус проекта: draft (черновик), active (в работе), archived (архивный)
    status = Column(String(50), nullable=False, default='draft', comment='Статус проекта')

    # Внешний ключ на таблицу кадастровых инженеров
    engineer_id = Column(Integer, ForeignKey('cadastralengineer.id'), nullable=False, comment='ID кадастрового инженера')

    # Связь с моделью CadastralEngineer (один проект – один инженер)
    engineer = relationship('CadastralEngineer', back_populates='projects', lazy='selectin')

    # Связь многие-ко-многим с заказчиками через промежуточную таблицу project_customer
    customers = relationship(
        'Customer',
        secondary='project_customer',
        back_populates='projects',
        lazy='selectin'
    )

    # Связь с участками (один проект – много участков)
    parcels = relationship(
        'Parcel',
        back_populates='project',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    # Связь с документами временно отключена, так как модель DocumentBase не определена.
    # При необходимости можно раскомментировать после создания модели DocumentBase.
    # documents = relationship(
    #     'DocumentBase',
    #     back_populates='project',
    #     cascade='all, delete-orphan',
    #     lazy='selectin'
    # )

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"