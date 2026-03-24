# tests/conftest.py
# Файл конфигурации pytest, содержащий общие фикстуры для всех тестов.
# Фикстуры автоматически доступны в любом тестовом модуле без явного импорта.

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Импортируем базовый класс моделей, чтобы создать таблицы в памяти
from src.models.base import Base
# Импортируем все модели, чтобы они были зарегистрированы в Base.metadata
from src.models import (
    LandCategory, AllowedUse, Region, GeopointMethod, EncumbranceType, DocumentType,
    CadastralEngineer, Customer, Project, Parcel, CharacteristicPoint, Contour,
    Adjacency, ParcelPart
)
# Импортируем сервисы, которые могут понадобиться в тестах
from src.services.project_service import ProjectService
from src.services.geometry_service import calculate_area, is_closed, is_self_intersecting

# Также можно импортировать вспомогательные функции для создания тестовых данных
from datetime import date


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Фикстура, создающая временную базу данных SQLite в памяти.
    База данных создаётся заново для каждой тестовой функции.
    После завершения теста все изменения откатываются, соединение закрывается.

    Returns:
        Объект сессии SQLAlchemy для работы с БД.
    """
    # Создаём движок для базы данных в памяти
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Создаём все таблицы согласно метаданным Base
    Base.metadata.create_all(engine)

    # Создаём фабрику сессий и открываем сессию
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    # Предоставляем сессию тесту
    yield session

    # После завершения теста закрываем сессию
    session.close()
    # (база данных в памяти автоматически уничтожается)


@pytest.fixture(scope="function")
def populated_db_session(db_session: Session) -> Session:
    """
    Фикстура, возвращающая сессию с предварительно заполненными справочными таблицами.
    Полезна для тестов, которым нужны справочники (категории земель, регионы и т.д.).
    """
    # Заполняем справочники минимально необходимыми записями
    # (можно вынести в отдельную функцию, но для краткости здесь)

    # Категории земель
    if db_session.query(LandCategory).count() == 0:
        categories = [
            LandCategory(code="003001000000", name="Земли сельскохозяйственного назначения"),
            LandCategory(code="003002000000", name="Земли населенных пунктов"),
        ]
        db_session.add_all(categories)

    # Регионы
    if db_session.query(Region).count() == 0:
        regions = [
            Region(code="77", name="Москва"),
            Region(code="78", name="Санкт-Петербург"),
        ]
        db_session.add_all(regions)

    # Методы определения координат
    if db_session.query(GeopointMethod).count() == 0:
        methods = [
            GeopointMethod(code="692001000000", name="Геодезический метод"),
            GeopointMethod(code="692005000000", name="Метод спутниковых геодезических измерений"),
        ]
        db_session.add_all(methods)

    # Типы обременений
    if db_session.query(EncumbranceType).count() == 0:
        enc_types = [
            EncumbranceType(code="022001000000", name="Сервитут"),
            EncumbranceType(code="022006000000", name="Аренда"),
        ]
        db_session.add_all(enc_types)

    db_session.commit()
    yield db_session


@pytest.fixture(scope="function")
def sample_engineer(db_session: Session) -> CadastralEngineer:
    """Создаёт тестового кадастрового инженера."""
    engineer = CadastralEngineer(
        family_name="Иванов",
        first_name="Иван",
        patronymic="Иванович",
        snils="12345678901",
        attestation_number="77-23-12345",
        date_entering=date(2020, 1, 1),
        phone="+71234567890",
        email="ivanov@example.com",
        address="г. Москва, ул. Ленина, д.1",
        sro_name="СРО Кадастровые инженеры"
    )
    db_session.add(engineer)
    db_session.commit()
    return engineer


@pytest.fixture(scope="function")
def sample_customer(db_session: Session) -> Customer:
    """Создаёт тестового заказчика (физическое лицо)."""
    customer = Customer(
        customer_type="person",
        family_name="Петров",
        first_name="Петр",
        patronymic="Петрович",
        snils="98765432101",
        phone="+79876543210",
        email="petrov@example.com"
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture(scope="function")
def sample_project(db_session: Session, sample_engineer: CadastralEngineer, sample_customer: Customer) -> Project:
    """Создаёт тестовый проект с инженером и заказчиком."""
    project = Project(
        name="Тестовый проект",
        description="Проект для автоматического тестирования",
        engineer=sample_engineer,
        status="draft"
    )
    project.customers.append(sample_customer)
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture(scope="function")
def sample_parcel(db_session: Session, sample_project: Project) -> Parcel:
    """Создаёт тестовый земельный участок (квадрат 10x10)."""
    from ..src.models import ParcelStatus, CharacteristicPoint

    parcel = Parcel(
        cadastral_number="77:01:0001001:123",
        status=ParcelStatus.NEW,
        cadastral_block="77:01:0001001",
        land_category_code="003002000000",
        address_region="77",
        address_or_location=1,
        area=100.0,
        area_inaccuracy=0.1,
        area_formula="По координатам",
        project=sample_project
    )
    db_session.add(parcel)
    db_session.commit()

    # Добавляем точки (квадрат)
    points = [
        CharacteristicPoint(point_number=1, x=0, y=0, parcel=parcel),
        CharacteristicPoint(point_number=2, x=10, y=0, parcel=parcel),
        CharacteristicPoint(point_number=3, x=10, y=10, parcel=parcel),
        CharacteristicPoint(point_number=4, x=0, y=10, parcel=parcel),
        CharacteristicPoint(point_number=5, x=0, y=0, parcel=parcel),  # замыкающая
    ]
    db_session.add_all(points)
    db_session.commit()
    return parcel