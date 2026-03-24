# src/utils/logger.py
# Модуль настройки логирования для всего приложения.
# Обеспечивает запись всех событий (информационных сообщений, предупреждений, ошибок)
# в файл и дублирование в консоль. Файлы логов сохраняются в директорию 'logs'
# с именем, содержащим дату и время запуска приложения.

import logging
import os
from datetime import datetime

# Имя директории для хранения логов
LOG_DIR = "logs"

# Создаём директорию, если она не существует
os.makedirs(LOG_DIR, exist_ok=True)

# Формируем имя файла лога на основе текущей даты и времени
# Пример: megevoy_20250228_153045.log
log_filename = os.path.join(
    LOG_DIR,
    f"megevoy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

# Настраиваем базовую конфигурацию корневого логгера
# Уровень логирования – DEBUG (будут записываться все сообщения от DEBUG и выше)
# Формат сообщения: время, уровень, имя логгера, само сообщение
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),  # запись в файл
        logging.StreamHandler()                               # вывод в консоль
    ]
)


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля, из которого вызывается).

    Returns:
        Объект Logger, настроенный согласно базовой конфигурации.
    """
    return logging.getLogger(name)