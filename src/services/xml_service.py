# src/services/xml_service.py
# Сервис для генерации XML-документа межевого плана в соответствии со схемой MP_v09.xsd.
# Использует библиотеку lxml для построения DOM-дерева и сериализации.

import uuid
from datetime import date
from typing import Optional, List
from lxml import etree

from ..models import (
    Project, Parcel, ParcelStatus, CharacteristicPoint, Contour,
    CadastralEngineer, Customer, Adjacency, ParcelPart
)
from ..utils.logger import get_logger
from ..utils.config import MP_SCHEMA  # путь к файлу схемы (для валидации, но не используется здесь)

logger = get_logger(__name__)


class XMLGenerator:
    """
    Генератор XML-документа межевого плана.
    На вход принимает объект Project и строит полное XML-дерево.
    """

    def __init__(self, project: Project):
        """
        Инициализация генератора.

        Args:
            project: Объект проекта, содержащий все данные для формирования межевого плана.
        """
        self.project = project
        # Пространства имён не требуются, так как схема не задаёт целевого namespace.
        # Однако в корневом элементе могут быть атрибуты, но xmlns не нужен.

    def generate(self) -> etree._Element:
        """
        Генерирует корневой элемент XML-документа.

        Returns:
            Корневой элемент <MP> с заполненными дочерними элементами.
        """
        # Корневой элемент
        root = etree.Element("MP")
        root.set("GUID", str(uuid.uuid4()))
        root.set("Version", "09")
        # Сведения о программном обеспечении (группа атрибутов agNeSoftware)
        root.set("NameSoftware", "MegevoyPlan")
        root.set("VersionSoftware", "1.0")

        # Пакет информации (Package)
        package = etree.SubElement(root, "Package")

        # В зависимости от статуса проекта и участков выбираем тип раздела.
        # В текущей реализации поддерживается только образование участков (FormParcels).
        # Можно расширить для других случаев (SpecifyParcel и т.д.).
        self._add_form_parcels(package)

        # Общие сведения о кадастровых работах
        general = etree.SubElement(root, "GeneralCadastralWorks")
        self._add_general_cadastral_works(general)

        # Исходные данные (InputData)
        input_data = etree.SubElement(root, "InputData")
        self._add_input_data(input_data)

        # Заключение кадастрового инженера (если есть)
        if self.project.description:
            conclusion = etree.SubElement(root, "Conclusion")
            conclusion.text = self.project.description

        # Схема геодезических построений (пока не генерируем, но элемент должен присутствовать)
        # По требованию ТЗ, PDF пока не генерируются, но структура закладывается.
        # Можно создать пустые элементы с заглушками или просто пропустить, если необязательно.
        # Согласно XSD, SchemeGeodesicPlotting необязателен, поэтому можем не добавлять.

        # Схема расположения земельных участков (аналогично)

        # Чертеж земельных участков и их частей (обязательный элемент)
        diagram = etree.SubElement(root, "DiagramParcelsSubParcels")
        self._add_diagram(diagram)

        # Акт согласования (если есть смежные участки)
        if any(p.adjacencies for p in self.project.parcels):
            agreement = etree.SubElement(root, "AgreementDocument")
            # Пока без файлов, только структура
            # В будущем здесь будет ссылка на PDF

        # Приложения (не реализовано)

        return root

    def _add_form_parcels(self, parent: etree._Element):
        """
        Добавляет раздел FormParcels (образование участков).
        В реальном проекте нужно учитывать различные способы образования (Method).
        Здесь для примера выбираем метод 5 (Образование из земель).
        """
        form_parcels = etree.SubElement(parent, "FormParcels")
        # Способ образования – пока жёстко 5 (образование из земель)
        form_parcels.set("Method", "5")

        # Для каждого участка со статусом NEW добавляем NewParcel
        for parcel in self.project.parcels:
            if parcel.status == ParcelStatus.NEW:
                self._add_new_parcel(form_parcels, parcel)

        # Здесь можно добавить ChangeParcel для изменённых участков,
        # SpecifyRelatedParcel для смежных и т.д.

    def _add_new_parcel(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет элемент NewParcel для образуемого участка.
        """
        new = etree.SubElement(parent, "NewParcel")
        # Обозначение образуемого участка (например, :ЗУ1)
        # В простейшем случае генерируем на основе ID участка
        new.set("Definition", f":ЗУ{parcel.id}")

        # Номер кадастрового квартала
        etree.SubElement(new, "CadastralBlock").text = parcel.cadastral_block

        # PrevCadastralNumbers – кадастровые номера исходных участков (если есть)
        # В текущей версии не заполняем

        # Сведения об обеспечении доступа – не заполняем

        # Объекты недвижимости на участке – не заполняем

        # Площадь
        self._add_area(new, parcel)

        # Адрес (местоположение)
        self._add_address(new, parcel)

        # Категория земель
        cat = etree.SubElement(new, "Category")
        cat.set("Category", parcel.land_category_code)
        # Документ о категории (не заполняем)

        # Лесная характеристика – не заполняем

        # Вид разрешенного использования
        self._add_permitted_use(new, parcel)

        # Части участка (обременения)
        if parcel.parts:
            self._add_sub_parcels(new, parcel)

        # Описание местоположения границ (координаты)
        if parcel.contours:
            # Многоконтурный участок
            self._add_contours(new, parcel)
        else:
            # Обычный участок
            self._add_entity_spatial(new, parcel)

        # Предельные размеры – не заполняем

        # Проект межевания – не заполняем

        # Иные сведения – не заполняем

    def _add_area(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет элемент Area с площадью и погрешностью.
        Для образуемых участков используется тип tAreaNew.
        """
        area_elem = etree.SubElement(parent, "Area")
        # Значение площади – округляем до целого числа (как требуется)
        area_value = int(round(parcel.area)) if parcel.area else 0
        etree.SubElement(area_elem, "Area").text = str(area_value)
        # Единица измерения – всегда 055 (квадратный метр)
        etree.SubElement(area_elem, "Unit").text = "055"
        # Погрешность – обязательна для tAreaNew
        inaccuracy = parcel.area_inaccuracy if parcel.area_inaccuracy else 0.1
        etree.SubElement(area_elem, "Inaccuracy").text = f"{inaccuracy:.2f}"
        # Формула – обязательна для tAreaNew
        formula = parcel.area_formula if parcel.area_formula else "По координатам характерных точек"
        etree.SubElement(area_elem, "Formula").text = formula

    def _add_address(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет структурированный адрес.
        Использует тип tAddressInpFullLocation.
        """
        address = etree.SubElement(parent, "Address")
        # Атрибут AddressOrLocation (1 – адрес, 0 – местоположение)
        address.set("AddressOrLocation", str(parcel.address_or_location))

        if parcel.address_fias:
            etree.SubElement(address, "FIAS").text = parcel.address_fias
        if parcel.address_postal_code:  # предполагаем, что есть такое поле (в модели может отсутствовать)
            etree.SubElement(address, "PostalCode").text = parcel.address_postal_code
        # Российская Федерация – опционально
        # etree.SubElement(address, "RussianFederation").text = "Российская Федерация"

        # Регион (обязателен)
        if parcel.address_region:
            etree.SubElement(address, "Region").text = parcel.address_region

        # Добавляем необязательные элементы с типом tAddressName (имя + тип)
        self._add_address_name(address, "District", parcel.address_district, "р-н")
        self._add_address_name(address, "City", parcel.address_city, "г")
        self._add_address_name(address, "UrbanDistrict", parcel.address_urban_district, "р-н")
        self._add_address_name(address, "SovietVillage", parcel.address_soviet_village, "с/с")
        self._add_address_name(address, "Locality", parcel.address_locality, "нп")
        self._add_address_name(address, "Street", parcel.address_street, "ул")

        # Номерные элементы (Level1, Level2, Level3, Apartment) – тип tNumberType
        self._add_number_type(address, "Level1", parcel.address_level1, "д")
        self._add_number_type(address, "Level2", parcel.address_level2, "к")
        self._add_number_type(address, "Level3", parcel.address_level3, "стр")
        self._add_number_type(address, "Apartment", parcel.address_apartment, "кв")

        if parcel.address_other:
            etree.SubElement(address, "Other").text = parcel.address_other
        if parcel.address_note:
            etree.SubElement(address, "Note").text = parcel.address_note

    def _add_address_name(self, parent: etree._Element, tag: str, value: Optional[str], type_str: str):
        """Добавляет элемент с атрибутами Name и Type, если value задано."""
        if value:
            elem = etree.SubElement(parent, tag)
            elem.set("Name", value)
            elem.set("Type", type_str)

    def _add_number_type(self, parent: etree._Element, tag: str, value: Optional[str], type_str: str):
        """Добавляет элемент с атрибутами Value и Type (для номерной части адреса)."""
        if value:
            elem = etree.SubElement(parent, tag)
            elem.set("Value", value)
            elem.set("Type", type_str)

    def _add_permitted_use(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет элемент PermittedUsesLand.
        """
        perm = etree.SubElement(parent, "PermittedUsesLand")

        if parcel.permitted_use_code:
            # Используем PermittedUsesOther (с кодом по классификатору)
            other = etree.SubElement(perm, "PermittedUsesOther")
            other.set("PermittedUseText", parcel.permitted_use_text or "")
            other.set("LandUse", parcel.permitted_use_code)
            # DocLandUse – можно добавить позже
        else:
            # Текстовое описание (без кода)
            est = etree.SubElement(perm, "PermittedUseEstablished")
            est.set("ByDocument", parcel.permitted_use_text or "")

    def _add_sub_parcels(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет сведения о частях участка (обременениях).
        Для образуемых участков используется тип tNewSubParcels.
        """
        sub_parcels = etree.SubElement(parent, "SubParcels")
        for part in parcel.parts:
            self._add_new_sub_parcel(sub_parcels, part)

    def _add_new_sub_parcel(self, parent: etree._Element, part: ParcelPart):
        """
        Добавляет элемент NewSubParcel.
        """
        new_sub = etree.SubElement(parent, "NewSubParcel")
        new_sub.set("Definition", part.account_number)

        # Площадь части
        area_elem = etree.SubElement(new_sub, "Area")
        etree.SubElement(area_elem, "Area").text = str(int(round(part.area)))
        etree.SubElement(area_elem, "Unit").text = "055"
        if part.area_inaccuracy:
            etree.SubElement(area_elem, "Inaccuracy").text = f"{part.area_inaccuracy:.2f}"
        if part.area_formula:
            etree.SubElement(area_elem, "Formula").text = part.area_formula

        # Характеристика части (ограничение/обременение)
        enc = etree.SubElement(new_sub, "Encumbrance")
        if part.restriction_name:
            etree.SubElement(enc, "Name").text = part.restriction_name
        etree.SubElement(enc, "Type").text = part.restriction_type_code
        if part.reg_numb_border:
            etree.SubElement(enc, "RegNumbBorder").text = part.reg_numb_border
        if part.cadastral_number_restriction:
            etree.SubElement(enc, "CadastralNumberRestriction").text = part.cadastral_number_restriction
        # Документы – не реализовано

        # Описание границ части (упрощённо – не реализуем)
        # В реальности нужно добавить EntitySpatial или Contours

    def _add_entity_spatial(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет элемент EntitySpatial для описания границ (обычный участок).
        """
        spatial = etree.SubElement(parent, "EntitySpatial")
        # Код системы координат (например, для Московской области зона 1 – "50.1")
        # В идеале брать из проекта
        spatial.set("CsCode", "50.1")
        # Наименование системы координат (опционально)
        spatial.set("Name", "МСК-50 зона 1")

        # SpatialElement – один замкнутый контур
        spatial_elem = etree.SubElement(spatial, "SpatialElement")
        for point in parcel.points:
            self._add_spelement_unit(spatial_elem, point)

        # Borders – описание частей границ от точки до точки (не реализовано)

    def _add_spelement_unit(self, parent: etree._Element, point: CharacteristicPoint):
        """
        Добавляет элемент SpelementUnit для точки (обычный участок).
        """
        sp_unit = etree.SubElement(parent, "SpelementUnit")
        sp_unit.set("TypeUnit", "Точка")

        ordinate = etree.SubElement(sp_unit, "Ordinate")
        ordinate.set("X", f"{point.x:.2f}")
        ordinate.set("Y", f"{point.y:.2f}")
        ordinate.set("NumGeopoint", str(point.point_number))
        if point.delta:
            ordinate.set("DeltaGeopoint", f"{point.delta:.2f}")
        if point.method_code:
            ordinate.set("GeopointOpred", point.method_code)
        if point.point_pref:
            ordinate.set("PointPref", point.point_pref)
        if point.description:
            ordinate.set("GeopointZacrep", point.description)
        if point.formula:
            ordinate.set("Formula", point.formula)

    def _add_contours(self, parent: etree._Element, parcel: Parcel):
        """
        Добавляет элемент Contours для многоконтурного участка.
        """
        contours_elem = etree.SubElement(parent, "Contours")
        for contour in parcel.contours:
            self._add_new_contour(contours_elem, contour)

    def _add_new_contour(self, parent: etree._Element, contour: Contour):
        """
        Добавляет элемент NewContour для многоконтурного участка.
        """
        new_contour = etree.SubElement(parent, "NewContour")
        new_contour.set("Definition", f"контур{contour.contour_number}")

        # Площадь контура
        area_elem = etree.SubElement(new_contour, "Area")
        etree.SubElement(area_elem, "Area").text = f"{contour.area:.2f}"
        etree.SubElement(area_elem, "Unit").text = "055"
        if contour.area_inaccuracy:
            etree.SubElement(area_elem, "Inaccuracy").text = f"{contour.area_inaccuracy:.2f}"
        if contour.area_formula:
            etree.SubElement(area_elem, "Formula").text = contour.area_formula

        # Описание границ контура
        spatial = etree.SubElement(new_contour, "EntitySpatial")
        spatial.set("CsCode", "50.1")  # условно
        spatial_elem = etree.SubElement(spatial, "SpatialElement")
        for point in contour.points:
            self._add_spelement_unit(spatial_elem, point)

        # Обеспечение доступа – не реализовано

    def _add_general_cadastral_works(self, parent: etree._Element):
        """
        Добавляет элемент GeneralCadastralWorks.
        """
        parent.set("DateCadastral", date.today().isoformat())

        # Contractor (кадастровый инженер)
        self._add_contractor(parent, self.project.engineer)

        # Reason (вид кадастровых работ)
        etree.SubElement(parent, "Reason").text = "Образование земельного участка"

        # Clients (заказчики)
        self._add_clients(parent, self.project.customers)

    def _add_contractor(self, parent: etree._Element, engineer: CadastralEngineer):
        """
        Добавляет элемент Contractor.
        """
        contractor = etree.SubElement(parent, "Contractor")

        # ФИО
        etree.SubElement(contractor, "FamilyName").text = engineer.family_name
        etree.SubElement(contractor, "FirstName").text = engineer.first_name
        if engineer.patronymic:
            etree.SubElement(contractor, "Patronymic").text = engineer.patronymic

        # ОГРНИП (если есть) – не заполняем
        # СНИЛС
        etree.SubElement(contractor, "SNILS").text = engineer.snils
        # Уникальный реестровый номер в СРО
        etree.SubElement(contractor, "CadastralEngineerRegistryNumber").text = engineer.attestation_number
        # Дата внесения в реестр СРО
        etree.SubElement(contractor, "DateEntering").text = engineer.date_entering.isoformat()
        # Телефон
        etree.SubElement(contractor, "Telephone").text = engineer.phone
        # Почтовый адрес
        etree.SubElement(contractor, "Address").text = engineer.address
        # Email (если есть)
        if engineer.email:
            etree.SubElement(contractor, "Email").text = engineer.email

        # Организация (если инженер работает в юрлице)
        if engineer.org_name:
            org = etree.SubElement(contractor, "Organization")
            etree.SubElement(org, "Name").text = engineer.org_name
            if engineer.org_address:
                etree.SubElement(org, "AddressOrganization").text = engineer.org_address

        # Наименование СРО
        etree.SubElement(contractor, "SelfRegulatoryOrganization").text = engineer.sro_name

        # Документ-основание (договор) – не заполняем

    def _add_clients(self, parent: etree._Element, customers: List[Customer]):
        """
        Добавляет элемент Clients со списком заказчиков.
        """
        clients_elem = etree.SubElement(parent, "Clients")
        for cust in customers:
            client = etree.SubElement(clients_elem, "Client")
            if cust.customer_type == 'person':
                person = etree.SubElement(client, "Person")
                etree.SubElement(person, "FamilyName").text = cust.family_name or ""
                etree.SubElement(person, "FirstName").text = cust.first_name or ""
                if cust.patronymic:
                    etree.SubElement(person, "Patronymic").text = cust.patronymic
                if cust.snils:
                    etree.SubElement(person, "SNILS").text = cust.snils
                # Документ (упрощённо)
                if cust.identity_document:
                    doc = etree.SubElement(person, "Document")
                    # Здесь нужно разбирать реквизиты, но для примера – код заглушка
                    etree.SubElement(doc, "CodeDocument").text = "008001001000"  # Паспорт РФ
                    etree.SubElement(doc, "Number").text = cust.identity_document
                    etree.SubElement(doc, "Date").text = date.today().isoformat()
                if cust.inn_person:
                    etree.SubElement(person, "INN").text = cust.inn_person
                # ОГРНИП – не заполняем
                if cust.phone:
                    etree.SubElement(person, "Telephone").text = cust.phone
                if cust.address:
                    etree.SubElement(person, "Address").text = cust.address
                if cust.email:
                    etree.SubElement(person, "Email").text = cust.email

            elif cust.customer_type == 'organization':
                org = etree.SubElement(client, "Organization")
                etree.SubElement(org, "Name").text = cust.full_name or ""
                etree.SubElement(org, "INN").text = cust.inn or ""
                etree.SubElement(org, "OGRN").text = cust.ogrn or ""
                # Контакты (опционально) – можно добавить
            elif cust.customer_type == 'governance':
                gov = etree.SubElement(client, "Governance")
                etree.SubElement(gov, "Name").text = cust.full_name or ""
                etree.SubElement(gov, "INN").text = cust.inn or ""
                etree.SubElement(gov, "OGRN").text = cust.ogrn or ""
            elif cust.customer_type == 'foreign':
                foreign = etree.SubElement(client, "ForeignOrganization")
                etree.SubElement(foreign, "Name").text = cust.full_name or ""
                etree.SubElement(foreign, "Country").text = cust.country or ""
                # остальные поля

    def _add_input_data(self, parent: etree._Element):
        """
        Добавляет элемент InputData (исходные данные).
        Здесь минимальное заполнение – список документов.
        """
        documents = etree.SubElement(parent, "Documents")
        # Можно добавить один документ-основание из проекта, если есть.
        # Для примера – пусто.

        # Геодезическая основа и средства измерений – не заполняем

    def _add_diagram(self, parent: etree._Element):
        """
        Добавляет элемент DiagramParcelsSubParcels (чертёж).
        Поскольку PDF не генерируются, добавляем пустой элемент с одним PDF-файлом-заглушкой,
        чтобы структура была валидной? Но согласно XSD, DiagramParcelsSubParcels имеет тип tAppliedFilesPDF,
        который требует хотя бы один AppliedFile. Однако в требованиях сказано, что формирование PDF будет позже,
        поэтому можно добавить фиктивный элемент с именем несуществующего файла, но это сделает XML невалидным.
        Лучше пропустить? Но XSD говорит, что DiagramParcelsSubParcels обязателен.
        Поэтому добавим элемент с заглушкой, но с пометкой, что файл будет создан позже.
        В реальной программе нужно генерировать чертёж и вставлять ссылку.
        """
        # Создаём AppliedFile с именем-заглушкой
        applied = etree.SubElement(parent, "AppliedFile")
        applied.set("Kind", "01")  # образ документа
        applied.set("Name", "diagram.pdf")  # имя файла, который будет создан

    def save(self, filepath: str):
        """
        Генерирует XML и сохраняет в файл.

        Args:
            filepath: Путь для сохранения файла.
        """
        root = self.generate()
        tree = etree.ElementTree(root)
        # Записываем с объявлением XML и отступами для читаемости
        tree.write(filepath, encoding="utf-8", xml_declaration=True, pretty_print=True)
        logger.info(f"XML межевого плана сохранён в {filepath}")