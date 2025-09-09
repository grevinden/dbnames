from contextlib import contextmanager
from pathlib import PurePosixPath
from typing import Literal, Generator
from uuid import UUID

import bom_decompressor
import curly_array
from sqlalchemy import Engine, select, column, table
from sqlalchemy.orm import sessionmaker

__all__ = ['metadata']

from sqlalchemy.util import immutabledict

from .metadata import MetaDataObjectTypes, MetaDataGroup, MetaDataTypes
from .models import MetaParserTableDocument, MetaParserValuesEnum
from .types import MetaData


@contextmanager
def files(
        engine: Engine,
        table_name: Literal["Params", "Config"],
        *,
        schema: str = "dbo"
) -> Generator[Generator[curly_array.core.NestedCurlyArray, str | UUID, None], None, None]:
    """Контекстный менеджер для работы с файлами метаданных"""

    with sessionmaker(bind=engine, autocommit=False)() as session:
        def file_generator():
            nonlocal session
            file_name = yield

            while True:
                stmt = select(column('BinaryData')).select_from(
                    table(table_name, column("FileName"), column("BinaryData"), schema=schema)
                ).where(column('FileName') == str(file_name)).limit(1)
                result: bytes = session.execute(stmt).scalar_one()
                parsed_data = curly_array.parse(bom_decompressor.decompress_and_decode(result))
                file_name = yield parsed_data

        gen = file_generator()
        next(gen)

        try:
            yield gen
        finally:
            gen.close()


def metadata(engine: Engine, /) -> MetaData:  #

    # Загружаем имена таблиц
    with files(engine, "Params") as params:
        names = {
            v[0]: f"_{v[1]}{v[2]}"
            for v in iter(params.send('DBNames')[1][0:])
            if (isinstance(v, list) and
                len(v) == 3 and
                isinstance(v[0], UUID) and
                v[0].int and
                v[1] in MetaDataObjectTypes)
        }

    # Словарь для хранения метаданных
    result = {}

    # Загружаем конфигурацию метаданных
    with files(engine, "Config") as config:

        config_data = config.send(config.send("root")[1])

        configuration = {}

        for v in iter(config_data):
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], UUID) \
                    and v[0] in MetaDataGroup and isinstance(v[1], list):

                for type_item in iter(v[1][1][3:]):
                    if type_item[0] in MetaDataTypes:
                        configuration[MetaDataTypes(type_item[0])] = [
                            config.send(obj_data) for obj_data in iter(type_item[2:])
                        ]

        # Создаем объекты документов
        for el in configuration[MetaDataTypes.Documents]:
            doc = MetaParserTableDocument(el, names=names)
            result[PurePosixPath('Таблица', 'Документ', repr(doc))] = doc

        # Создаем объекты перечислений
        for el in configuration[MetaDataTypes.Enums]:
            enum = MetaParserValuesEnum(el)
            result[PurePosixPath('Значения', 'Перечисление', repr(enum))] = enum

    return immutabledict(result)
