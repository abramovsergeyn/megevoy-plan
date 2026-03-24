# src/models/customer.py
# Модель заказчика кадастровых работ.
# Поддерживает различные типы: физическое лицо, юридическое лицо,
# орган государственной власти / местного самоуправления, иностранное юридическое лицо.

from sqlalchemy import Column, Integer, String, Date, Table, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


# Промежуточная таблица для связи многие-ко-многим между проектами и заказчиками
project_customer = Table(
    'project_customer',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
    Column('customer_id', Integer, ForeignKey('customer.id'), primary_key=True)
)


class Customer(Base):
    """
    Заказчик кадастровых работ.
    Может быть:
    - физическим лицом (person)
    - юридическим лицом (organization)
    - органом государственной власти или местного самоуправления (governance)
    - иностранным юридическим лицом (foreign_organization)
    """
    __tablename__ = 'customer'

    # Общие поля для всех типов

    # Тип заказчика (одно из значений: person, organization, governance, foreign)
    customer_type = Column(String(20), nullable=False, comment='Тип заказчика')

    # Контактные данные (общие для всех)
    phone = Column(String(50), nullable=True, comment='Контактный телефон')
    email = Column(String(100), nullable=True, comment='Адрес электронной почты')
    address = Column(String(4000), nullable=True, comment='Почтовый адрес / адрес местонахождения')

    # Поля для физического лица (customer_type = 'person')
    family_name = Column(String(100), nullable=True, comment='Фамилия (для физлица)')
    first_name = Column(String(100), nullable=True, comment='Имя (для физлица)')
    patronymic = Column(String(100), nullable=True, comment='Отчество (для физлица)')
    snils = Column(String(11), nullable=True, comment='СНИЛС (для физлица)')
    inn_person = Column(String(12), nullable=True, comment='ИНН физического лица (12 цифр)')
    # Документ, удостоверяющий личность – можно вынести в отдельную таблицу, но для упрощения храним текстом
    identity_document = Column(String(500), nullable=True, comment='Реквизиты документа, удостоверяющего личность')

    # Поля для юридического лица и органа власти (customer_type = 'organization' или 'governance')
    full_name = Column(String(500), nullable=True, comment='Полное наименование организации')
    inn = Column(String(10), nullable=True, comment='ИНН юридического лица (10 цифр)')
    ogrn = Column(String(13), nullable=True, comment='ОГРН (13 цифр)')

    # Поля для иностранного юридического лица (customer_type = 'foreign')
    country = Column(String(255), nullable=True, comment='Страна регистрации (инкорпорации)')
    reg_number = Column(String(50), nullable=True, comment='Регистрационный номер в стране')
    reg_date = Column(Date, nullable=True, comment='Дата регистрации')

    # Связь с проектами (многие-ко-многим)
    projects = relationship('Project', secondary=project_customer, back_populates='customers', lazy='selectin')

    def __repr__(self):
        if self.customer_type == 'person':
            name = f"{self.family_name} {self.first_name}"
        else:
            name = self.full_name or ''
        return f"<Customer(id={self.id}, type='{self.customer_type}', name='{name}')>"