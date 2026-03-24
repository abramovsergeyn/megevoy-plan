# src/utils/init_db.py
# Модуль инициализации базы данных.
# Выполняет создание всех таблиц на основе моделей SQLAlchemy,
# заполняет справочные таблицы (словари) начальными данными из JSON-файлов,
# а также создаёт демонстрационные данные (инженер, заказчик, проект, участок)
# при первом запуске приложения.

import json
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импортируем базовый класс моделей и все классы моделей
from ..models import (
    Base,
    LandCategory,
    AllowedUse,
    Region,
    GeopointMethod,
    EncumbranceType,
    DocumentType,
    CadastralEngineer,
    Customer,
    Project,
    Parcel,
    ParcelStatus,
    CharacteristicPoint
)
from .config import DICTIONARIES_DIR
from .logger import get_logger

logger = get_logger(__name__)


def load_json(filename: str):
    """
    Загружает данные из JSON-файла и возвращает список словарей.
    Предполагается, что файл содержит массив объектов с полями code и name.

    Args:
        filename: Имя файла (без пути).

    Returns:
        Список словарей, каждый с ключами code и name (или другими, если файл имеет иную структуру).
        В случае ошибки возвращает пустой список.
    """
    filepath = DICTIONARIES_DIR / filename
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Загружен файл {filename}, записей: {len(data)}")
        return data
    except Exception as e:
        logger.exception(f"Ошибка загрузки файла {filename}: {e}")
        return []


def create_demo_data(session):
    """
    Создаёт демонстрационные данные, если соответствующие таблицы пусты.
    Инженер, заказчик, проект и земельный участок с характерными точками.
    """
    # Создаём инженера, если их нет
    if session.query(CadastralEngineer).count() == 0:
        logger.info("Создание демо-инженера")
        engineer = CadastralEngineer(
            family_name="Иванов",
            first_name="Иван",
            patronymic="Иванович",
            snils="12345678901",
            attestation_number="77-23-12345",
            date_entering=date(2020, 1, 1),
            phone="+7 (123) 456-78-90",
            email="ivanov@example.com",
            address="г. Москва, ул. Ленина, д.1",
            sro_name="СРО Кадастровые инженеры"
        )
        session.add(engineer)
        session.flush()  # чтобы получить id
    else:
        engineer = session.query(CadastralEngineer).first()

    # Создаём заказчика, если их нет
    if session.query(Customer).count() == 0:
        logger.info("Создание демо-заказчика")
        customer = Customer(
            customer_type="person",
            family_name="Петров",
            first_name="Пётр",
            patronymic="Петрович",
            snils="98765432101",
            phone="+7 (987) 654-32-10",
            email="petrov@example.com"
        )
        session.add(customer)
        session.flush()
    else:
        customer = session.query(Customer).first()

    # Создаём проект, если их нет, и есть инженер и заказчик
    if session.query(Project).count() == 0 and engineer and customer:
        logger.info("Создание демо-проекта")
        project = Project(
            name="Тестовый проект",
            description="Демонстрационный проект для ознакомления",
            engineer_id=engineer.id,
            status="draft"
        )
        project.customers.append(customer)
        session.add(project)
        session.flush()

        # Создаём участок (квадрат 20x20)
        parcel = Parcel(
            cadastral_number="77:01:0001001:123",
            status=ParcelStatus.NEW,
            cadastral_block="77:01:0001001",
            land_category_code="003002000000",  # Земли населенных пунктов
            address_region="77",                 # Москва
            address_or_location=1,
            area=400.0,
            area_inaccuracy=0.1,
            area_formula="По координатам",
            project_id=project.id
        )
        session.add(parcel)
        session.flush()

        # Точки квадрата (замкнутый контур)
        points = [
            CharacteristicPoint(point_number=1, x=0, y=0, parcel_id=parcel.id),
            CharacteristicPoint(point_number=2, x=20, y=0, parcel_id=parcel.id),
            CharacteristicPoint(point_number=3, x=20, y=20, parcel_id=parcel.id),
            CharacteristicPoint(point_number=4, x=0, y=20, parcel_id=parcel.id),
            CharacteristicPoint(point_number=5, x=0, y=0, parcel_id=parcel.id),  # замыкающая
        ]
        session.add_all(points)
        session.commit()
        logger.info("Демо-данные успешно созданы")
    else:
        session.commit()


def init_db(engine):
    """
    Инициализирует базу данных:
    - создаёт все таблицы (если они ещё не существуют);
    - заполняет справочные таблицы данными из JSON-файлов,
      если таблицы пусты;
    - создаёт демонстрационные данные, если основных таблиц нет.

    Args:
        engine: Объект SQLAlchemy Engine, подключённый к целевой БД.
    """
    # Создаём таблицы
    Base.metadata.create_all(engine)
    logger.info("Таблицы базы данных созданы (или уже существовали)")

    # Создаём сессию для загрузки данных
    Session = sessionmaker(bind=engine)
    session = Session()

    # Функция для заполнения таблицы, если она пуста
    def fill_if_empty(model, filename, code_field='code', name_field='name'):
        """
        Заполняет таблицу model данными из JSON-файла, если таблица пуста.
        """
        if session.query(model).count() == 0:
            records = load_json(filename)
            for item in records:
                obj = model(
                    code=item[code_field],
                    name=item[name_field]
                )
                session.add(obj)
            session.commit()
            logger.info(f"Таблица {model.__tablename__} заполнена {len(records)} записями из {filename}")
        else:
            logger.info(f"Таблица {model.__tablename__} уже содержит данные, пропускаем заполнение")

    # Заполняем справочные таблицы
    fill_if_empty(LandCategory, "categories.json")
    fill_if_empty(AllowedUse, "allowed_use.json")
    fill_if_empty(Region, "regions.json")
    fill_if_empty(GeopointMethod, "methods.json")
    fill_if_empty(EncumbranceType, "encumbrances.json")
    fill_if_empty(DocumentType, "documents.json")

    # Создаём демонстрационные данные (инженер, заказчик, проект, участок)
    create_demo_data(session)

    # Закрываем сессию
    session.close()
    logger.info("Инициализация базы данных завершена")