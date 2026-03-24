# src/main.py
# Точка входа в приложение «Межевой план»
# Запускает графический интерфейс, инициализирует базу данных и логирование.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Добавляем путь к родительской папке, чтобы импорты работали при запуске из любой директории
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импортируем утилиты и главное окно
from src.utils.config import DATABASE_URL
from src.utils.logger import get_logger
from src.utils.init_db import init_db
from src.gui.main_window import MainWindow


def main():
    """
    Главная функция приложения:
    - инициализирует логирование;
    - создаёт подключение к базе данных SQLite;
    - создаёт таблицы и заполняет справочники (если необходимо);
    - запускает главное окно приложения.
    """
    # Настраиваем корневой логгер (файл + консоль)
    logger = get_logger(__name__)
    logger.info("Запуск приложения «Межевой план»")

    # Создаём экземпляр QApplication (обязательно до любых оконных объектов)
    app = QApplication(sys.argv)
    app.setApplicationName("Межевой план")
    app.setOrganizationName("MegevoyPlan")

    # Подключаемся к базе данных
    # DATABASE_URL определён в config.py, например "sqlite:///megevoy.db"
    engine = create_engine(DATABASE_URL, echo=False)  # echo=False отключает вывод SQL в консоль
    logger.info(f"Подключение к БД: {DATABASE_URL}")

    # Инициализация базы данных: создание таблиц и загрузка справочников
    try:
        init_db(engine)
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.exception("Ошибка инициализации базы данных")
        # Можно показать сообщение пользователю, но проще выйти
        sys.exit(1)

    # Создаём фабрику сессий и открываем сессию для работы с БД
    Session = sessionmaker(bind=engine)
    session = Session()

    # Создаём и показываем главное окно, передавая ему сессию
    window = MainWindow(session)
    window.show()

    # Запускаем главный цикл обработки событий Qt
    exit_code = app.exec()

    # Закрываем сессию перед выходом
    session.close()
    logger.info("Приложение завершено")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()