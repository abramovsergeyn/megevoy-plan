# src/models/base.py
# Базовый класс для всех моделей SQLAlchemy.
# Содержит общие поля (id, created_at, updated_at) и настройки для именования таблиц.

from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    """
    Базовый класс-примесь (mixin), который добавляет общие атрибуты и поведение
    для всех моделей данных. Не является самостоятельной таблицей.
    """

    # Автоматическое именование таблицы по имени класса в нижнем регистре.
    # Например, класс Project → таблица 'project'.
    @declared_attr
    def __tablename__(cls):
        """
        Возвращает имя таблицы, автоматически формируемое из имени класса.
        Используется SQLAlchemy для генерации названия таблицы, если оно не задано явно.
        """
        return cls.__name__.lower()

    # Первичный ключ — автоинкрементное целое число.
    id = Column(Integer, primary_key=True, index=True)

    # Дата и время создания записи.
    # server_default=func.now() устанавливает значение на стороне сервера БД
    # (например, CURRENT_TIMESTAMP в SQLite).
    created_at = Column(DateTime, server_default=func.now())

    # Дата и время последнего обновления записи.
    # onupdate=func.now() автоматически обновляет это поле при каждом изменении строки.
    updated_at = Column(DateTime, onupdate=func.now())


# Создаём экземпляр декларативной базы, используя наш базовый класс-примесь.
# Все модели должны наследоваться от этой базы (например, class MyModel(Base)).
Base = declarative_base(cls=Base)