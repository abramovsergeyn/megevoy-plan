# src/models/engineer.py
# Модель кадастрового инженера.
# Содержит все необходимые сведения о лице, выполняющем кадастровые работы.

from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from .base import Base


class CadastralEngineer(Base):
    """
    Кадастровый инженер – физическое лицо, имеющее квалификационный аттестат
    и состоящее в саморегулируемой организации (СРО).
    """
    __tablename__ = 'cadastralengineer'

    # Фамилия (обязательно)
    family_name = Column(String(100), nullable=False, comment='Фамилия')

    # Имя (обязательно)
    first_name = Column(String(100), nullable=False, comment='Имя')

    # Отчество (может отсутствовать)
    patronymic = Column(String(100), nullable=True, comment='Отчество')

    # СНИЛС – 11 цифр (уникальный идентификатор)
    snils = Column(String(11), unique=True, nullable=False, comment='СНИЛС (11 цифр)')

    # Номер квалификационного аттестата кадастрового инженера
    # Формат: две цифры региона, тире, две цифры года, тире, порядковый номер
    # Пример: 77-23-12345
    attestation_number = Column(String(50), nullable=False, comment='Номер квалификационного аттестата')

    # Дата внесения сведений о физическом лице в реестр СРО
    date_entering = Column(Date, nullable=False, comment='Дата внесения в реестр СРО')

    # Контактный телефон (обязательно)
    phone = Column(String(50), nullable=False, comment='Контактный телефон')

    # Адрес электронной почты (необязательно)
    email = Column(String(100), nullable=True, comment='Адрес электронной почты')

    # Почтовый адрес для связи
    address = Column(String(4000), nullable=False, comment='Почтовый адрес')

    # Наименование саморегулируемой организации, членом которой является инженер
    sro_name = Column(String(255), nullable=False, comment='Наименование СРО')

    # Дополнительные сведения о юридическом лице, если инженер работает по найму
    # (заполняется, если инженер не является индивидуальным предпринимателем)
    org_name = Column(String(2000), nullable=True, comment='Наименование юридического лица')
    org_address = Column(String(4000), nullable=True, comment='Адрес юридического лица')

    # Связь с проектами: один инженер может вести множество проектов
    projects = relationship('Project', back_populates='engineer', lazy='selectin')

    def __repr__(self):
        return f"<CadastralEngineer(id={self.id}, name='{self.family_name} {self.first_name}', snils='{self.snils}')>"