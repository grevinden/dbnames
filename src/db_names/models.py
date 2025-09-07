from abc import ABCMeta
from functools import cached_property
from typing import final, TypedDict, ReadOnly
from uuid import UUID

from frozendict import frozendict
from pydantic import RootModel


class FrozenMeta(ABCMeta):
    """Метакласс для создания замороженных классов"""

    def __new__(mcls, name, bases, namespace, **kwargs):
        # Создаем класс как обычно
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        # Делаем класс замороженным, переопределяя методы
        original_setattr = getattr(cls, '__setattr__', None)

        def frozen_setattr(self, name, value):
            if hasattr(self, '_initialized') and self._initialized:
                raise AttributeError(f"Cannot set attribute '{name}' on frozen class '{self.__class__.__name__}'")
            if original_setattr:
                original_setattr(self, name, value)
            else:
                object.__setattr__(self, name, value)

        def frozen_delattr(self, name):
            raise AttributeError(f"Cannot delete attribute '{name}' from frozen class '{self.__class__.__name__}'")

        cls.__setattr__ = frozen_setattr
        cls.__delattr__ = frozen_delattr

        return cls


class BaseElement(metaclass=FrozenMeta):
    """Базовый замороженный класс для элементов метаданных"""

    def __init__(self, name: str, table: str) -> None:
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_table', table)
        object.__setattr__(self, '_initialized', True)

    def __str__(self) -> str:
        return self._table

    def __repr__(self) -> str:
        return self._name


class VersionedElement(metaclass=FrozenMeta):
    """Замороженный класс для версионированных элементов"""
    ВерсияДанных: str = "_Version"


class LinkedElement(metaclass=FrozenMeta):
    """Замороженный класс для элементов со ссылками"""
    Ссылка: str = "_IDRRef"


class DeletableElement(metaclass=FrozenMeta):
    """Замороженный класс для удаляемых элементов"""
    ПометкаУдаления: str = "_Marked"


class NumberedElement(metaclass=FrozenMeta):
    """Замороженный класс для нумерованных элементов"""
    Номер: str = "_Number"


@final
class MetaParserDocument(DeletableElement, NumberedElement, LinkedElement, VersionedElement, BaseElement):
    """Финальный замороженный класс для документов метаданных"""

    def __init__(self, names: dict, meta: list) -> None:
        name = meta[1][9][1][2]
        table = names[meta[1][9][1][1][2]]

        # Инициализируем базовый класс
        super().__init__(name, table)

        # Устанавливаем свойства
        prop = frozendict({
            v[0][1][1][1][2]: names[v[0][1][1][1][1][2]]
            for v in iter(meta[5][2:])
        })
        object.__setattr__(self, '_prop', prop)

        # Устанавливаем константы
        object.__setattr__(self, 'Дата', "_Date_Time")
        object.__setattr__(self, 'Проведен', "_Posted")

    def __getattr__(self, item: str) -> str:
        return self._prop[item]


@final
class MetaParserEnum(BaseElement):
    """Финальный замороженный класс для перечислений метаданных"""

    def __init__(self, names: dict, meta: list) -> None:
        name = meta[1][5][1][2]
        table = names[meta[1][5][1][1][2]]

        # Инициализируем базовый класс
        super().__init__(name, table)

        # Устанавливаем свойства
        prop = frozendict({
            v[0][1][2]: v[0][1][1][2]
            for v in iter(meta[6][2:])
        })
        object.__setattr__(self, '_prop', prop)

    def __getattr__(self, item: str) -> UUID:
        return self._prop[item]

    class EnumRow(TypedDict):
        name: ReadOnly[str]
        guid: ReadOnly[UUID]

    @cached_property
    def rowset(self) -> list[EnumRow]:
        """Кэшированное свойство для набора данных перечисления"""
        return RootModel[list['MetaParserEnum.EnumRow']].model_validate([
            dict(name=k, guid=v) for k, v in self._prop.items()
        ]).root
