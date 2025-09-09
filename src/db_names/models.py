from abc import ABCMeta
from functools import cached_property
from typing import Final, final
from uuid import UUID

__all__ = ["MetaParserTableDocument", "MetaParserValuesEnum"]

from sqlalchemy import Values, column, values, TypeDecorator, types, NVARCHAR


class NamedMixin(metaclass=ABCMeta):
    """Базовый класс для элементов метаданных"""

    _Наименование: Final[str]

    def __init__(self, name: str, /) -> None:
        self._Наименование = name

    def __repr__(self) -> str:
        return self._Наименование


class TableMixin(metaclass=ABCMeta):
    """Базовый класс для элементов метаданных"""

    _ТаблицаДанных: Final[str]

    def __init__(self, table: str, /) -> None:
        self._ТаблицаДанных = table

    def __str__(self) -> str:
        return self._ТаблицаДанных


class VersionedMixin(metaclass=ABCMeta):
    ВерсияДанных: Final[str] = "_Version"


class LinkedMixin(metaclass=ABCMeta):
    Ссылка: Final[str] = "_IDRRef"


class DeletableMixin(metaclass=ABCMeta):
    ПометкаУдаления: Final[str] = "_Marked"


class NumberedMixin(metaclass=ABCMeta):
    Номер: Final[str] = "_Number"


class DatedMixin(metaclass=ABCMeta):
    Дата: Final[str] = "_Date_Time"


class FieldsMixin(metaclass=ABCMeta):
    _Реквизиты: Final[dict[str, str | UUID]]

    def __init__(self, prop: dict[str, str], /) -> None:
        self._Реквизиты = prop

    def __getattr__(self, name: str) -> str:
        return self._Реквизиты[name]


@final
class MetaParserTableDocument(
    FieldsMixin, DatedMixin, DeletableMixin, NumberedMixin, LinkedMixin, VersionedMixin, TableMixin, NamedMixin):
    """Класс для представления документов метаданных"""

    Проведен: Final[str] = "_Posted"

    def __init__(self, meta: list, /, *, names: dict[UUID, str]) -> None:  #

        name = meta[1][9][1][2]
        NamedMixin.__init__(self, name)

        table = names[meta[1][9][1][1][2]]
        TableMixin.__init__(self, table)

        prop = {prop[0][1][1][1][2]: names[prop[0][1][1][1][1][2]] for prop in iter(meta[5][2:])}
        FieldsMixin.__init__(self, prop)


class LiteralBINARY(TypeDecorator):
    impl = types.BINARY
    cache_ok = True

    def literal_processor(self, dialect):
        def process(value: bytes)->str:
            return f"0x{value.hex().upper()}"

        return process



@final
class MetaParserValuesEnum(NamedMixin, FieldsMixin):
    """Класс для представления перечислений метаданных"""

    def __init__(self, meta: list, /) -> None:
        NamedMixin.__init__(self, meta[1][5][1][2])
        FieldsMixin.__init__(self, {item[0][1][2]: item[0][1][1][2] for item in iter(meta[6][2:])})

    @cached_property
    def values(self) -> Values:
        return values(
            column('name', NVARCHAR),
            column('guid', LiteralBINARY(16)),
            literal_binds=True, name=self._Наименование
        ).data([(k, v.bytes) for k, v in self._Реквизиты.items()])
