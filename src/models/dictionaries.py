# src/models/dictionaries.py
# Модели для справочных данных (классификаторов), используемых в межевом плане.
# Все модели наследуются от Base и хранят пары "код – наименование".

from sqlalchemy import Column, Integer, String
from .base import Base  # Импортируем базовый класс из текущего пакета


class LandCategory(Base):
    """
    Категории земель в соответствии с классификатором dCategories.
    Источник: Приказ Росреестра, справочник 003 (ESUNSI).
    Примеры: 003001000000 – Земли сельскохозяйственного назначения,
             003002000000 – Земли населенных пунктов.
    """
    __tablename__ = 'land_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)          # Внутренний идентификатор
    code = Column(String(12), unique=True, nullable=False, index=True)  # Код категории (ровно 12 символов)
    name = Column(String(255), nullable=False)                          # Наименование категории

    def __repr__(self):
        return f"<LandCategory(code='{self.code}', name='{self.name}')>"


class AllowedUse(Base):
    """
    Виды разрешенного использования земельных участков по классификатору dAllowedUse.
    Код состоит из 12 цифр, соответствует Приказу Росреестра.
    Пример: 214001001000 – Растениеводство.
    """
    __tablename__ = 'allowed_uses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), unique=True, nullable=False, index=True)  # Код вида разрешенного использования
    name = Column(String(500), nullable=False)                          # Описание вида

    def __repr__(self):
        return f"<AllowedUse(code='{self.code}', name='{self.name}')>"


class Region(Base):
    """
    Субъекты Российской Федерации (регионы) по справочнику dRegionsRF.
    Код состоит из 2 цифр.
    Пример: 77 – Москва, 78 – Санкт-Петербург.
    """
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(2), unique=True, nullable=False, index=True)   # Код региона (2 цифры)
    name = Column(String(255), nullable=False)                          # Наименование региона

    def __repr__(self):
        return f"<Region(code='{self.code}', name='{self.name}')>"


class GeopointMethod(Base):
    """
    Методы определения координат характерных точек по справочнику dGeopointOpred.
    Код 12 цифр.
    Пример: 692001000000 – Геодезический метод,
             692005000000 – Метод спутниковых геодезических измерений.
    """
    __tablename__ = 'geopoint_methods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), unique=True, nullable=False, index=True)  # Код метода
    name = Column(String(255), nullable=False)                          # Название метода

    def __repr__(self):
        return f"<GeopointMethod(code='{self.code}', name='{self.name}')>"


class EncumbranceType(Base):
    """
    Виды ограничений (обременений) по справочнику dEncumbrances.
    Код 12 цифр.
    Пример: 022001000000 – Сервитут, 022006000000 – Аренда.
    """
    __tablename__ = 'encumbrance_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), unique=True, nullable=False, index=True)  # Код ограничения
    name = Column(String(500), nullable=False)                          # Описание ограничения

    def __repr__(self):
        return f"<EncumbranceType(code='{self.code}', name='{self.name}')>"


class DocumentType(Base):
    """
    Виды документов по справочнику dAllDocuments.
    Код 12 цифр, структурирован по разделам.
    Пример: 558203000000 – Межевой план, 008001001000 – Паспорт гражданина РФ.
    """
    __tablename__ = 'document_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), unique=True, nullable=False, index=True)  # Код документа
    name = Column(String(500), nullable=False)                          # Наименование документа

    def __repr__(self):
        return f"<DocumentType(code='{self.code}', name='{self.name}')>"