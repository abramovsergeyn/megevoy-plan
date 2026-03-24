# src/services/project_service.py
# Сервис для управления проектами межевания.
# Предоставляет методы для создания, чтения, обновления и удаления проектов,
# а также для работы с проектами в рамках сессии базы данных.

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models import Project, CadastralEngineer, Customer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProjectService:
    """
    Сервисный класс для операций с проектами.
    Инкапсулирует логику работы с БД и бизнес-правила, связанные с проектами.
    """

    def __init__(self, session: Session):
        """
        Инициализация сервиса.

        Args:
            session: Сессия SQLAlchemy для работы с базой данных.
        """
        self.session = session

    def create_project(self, name: str, engineer_id: int, customer_ids: List[int],
                       description: Optional[str] = None) -> Optional[Project]:
        """
        Создаёт новый проект.

        Args:
            name: Наименование проекта.
            engineer_id: ID кадастрового инженера (ответственного за проект).
            customer_ids: Список ID заказчиков.
            description: Описание проекта (необязательно).

        Returns:
            Объект созданного проекта или None в случае ошибки.
        """
        try:
            # Проверяем существование инженера
            engineer = self.session.get(CadastralEngineer, engineer_id)
            if not engineer:
                logger.error(f"Инженер с ID {engineer_id} не найден")
                return None

            # Создаём проект
            project = Project(
                name=name,
                description=description,
                engineer_id=engineer_id,
                status='draft'
            )

            # Добавляем заказчиков
            customers = self.session.query(Customer).filter(Customer.id.in_(customer_ids)).all()
            if len(customers) != len(customer_ids):
                missing = set(customer_ids) - {c.id for c in customers}
                logger.warning(f"Некоторые заказчики не найдены: {missing}")
            project.customers = customers

            self.session.add(project)
            self.session.commit()
            logger.info(f"Создан проект ID={project.id}, name='{name}'")
            return project

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Ошибка при создании проекта")
            return None

    def get_project(self, project_id: int) -> Optional[Project]:
        """
        Получает проект по его идентификатору.

        Args:
            project_id: ID проекта.

        Returns:
            Объект Project или None, если проект не найден.
        """
        try:
            project = self.session.get(Project, project_id)
            if project:
                logger.debug(f"Загружен проект ID={project_id}")
            else:
                logger.warning(f"Проект с ID {project_id} не найден")
            return project
        except SQLAlchemyError as e:
            logger.exception("Ошибка при загрузке проекта")
            return None

    def get_all_projects(self) -> List[Project]:
        """
        Возвращает список всех проектов.

        Returns:
            Список проектов (может быть пустым).
        """
        try:
            projects = self.session.query(Project).all()
            logger.debug(f"Загружено {len(projects)} проектов")
            return projects
        except SQLAlchemyError as e:
            logger.exception("Ошибка при загрузке списка проектов")
            return []

    def update_project(self, project_id: int, **kwargs: Dict[str, Any]) -> Optional[Project]:
        """
        Обновляет поля проекта.

        Args:
            project_id: ID проекта.
            **kwargs: Именованные аргументы для обновления (name, description, engineer_id, status, customer_ids).

        Returns:
            Обновлённый объект проекта или None в случае ошибки.
        """
        try:
            project = self.session.get(Project, project_id)
            if not project:
                logger.error(f"Проект с ID {project_id} не найден")
                return None

            # Обновляем простые поля
            for key in ['name', 'description', 'engineer_id', 'status']:
                if key in kwargs:
                    setattr(project, key, kwargs[key])

            # Обновление заказчиков
            if 'customer_ids' in kwargs:
                customers = self.session.query(Customer).filter(
                    Customer.id.in_(kwargs['customer_ids'])
                ).all()
                project.customers = customers

            self.session.commit()
            logger.info(f"Проект ID={project_id} обновлён")
            return project

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Ошибка при обновлении проекта")
            return None

    def delete_project(self, project_id: int) -> bool:
        """
        Удаляет проект.

        Args:
            project_id: ID проекта.

        Returns:
            True, если удаление успешно, иначе False.
        """
        try:
            project = self.session.get(Project, project_id)
            if not project:
                logger.error(f"Проект с ID {project_id} не найден")
                return False

            self.session.delete(project)
            self.session.commit()
            logger.info(f"Проект ID={project_id} удалён")
            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Ошибка при удалении проекта")
            return False

    def save_project(self, project: Project) -> bool:
        """
        Сохраняет изменения существующего проекта (коммит).

        Args:
            project: Объект проекта.

        Returns:
            True, если сохранение успешно, иначе False.
        """
        try:
            self.session.commit()
            logger.debug(f"Изменения проекта ID={project.id} сохранены")
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Ошибка при сохранении проекта")
            return False