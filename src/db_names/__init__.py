from abc import ABC
from contextlib import contextmanager
from enum import Enum, unique, StrEnum
from pathlib import PurePosixPath
from typing import Literal, cast, Generator, final
from uuid import UUID

import bom_decompressor
import curly_array
from frozendict import frozendict
import orjson
import sqlmodel
from pydantic import BaseModel, Field, AliasPath
from sqlalchemy import create_engine, Engine, ScalarResult, column, table
from sqlmodel import Session


# noinspection PyDataclass
class DBName(BaseModel, frozen=True):
    uid: UUID = Field(validation_alias=AliasPath("root", 0))
    name: str = Field(validation_alias=AliasPath("root", 1))
    id: int = Field(validation_alias=AliasPath("root", 2))

    def __str__(self):
        return f"_{self.name}{self.id}"


engine = create_engine(
    "mssql+pyodbc://sa:yDeapxJXEvtWCLh8uGm4KA@1c-sql.delta.local:1433/processing"
    "?" "driver=ODBC+DRIVER+18+FOR+SQL+SERVER"
    "&" "TrustServerCertificate=Yes"
    , echo=True)


# noinspection PyShadowingNames,SpellCheckingInspection
@contextmanager
def files(
        engine: Engine, tname: Literal["Params", "Config"], *, schema: str = "dbo"
) -> Generator[Generator[curly_array.NestedCurlyArray, str | UUID, None]]:  #

    with Session(engine, autocommit=False) as session:
        def file_generator():
            nonlocal session
            file_name = yield

            while True:
                # noinspection PyTypeChecker,Pydantic
                file_name: str | UUID = \
                    yield curly_array.parse(bom_decompressor.decompress_and_decode(
                        cast(ScalarResult, session.exec(
                            sqlmodel.select(column('BinaryData')).select_from(
                                table(tname, column("FileName"), column("BinaryData"), schema=schema)
                            ).where(column('FileName') == str(file_name)).limit(1)
                        )).one()))

        next(fg := file_generator())

        try:
            yield fg
        finally:
            fg.close()


@unique
class MetaDataGroup(Enum):
    Main = UUID('9fcd25a0-4822-11d4-9414-008048da11f9')


@unique
class MetaDataTypes(Enum):
    Documents = UUID("061d872a-5787-460e-95ac-ed74ea3a3e84")
    Enums = UUID("f6a80749-5ad7-400b-8519-39dc5dff2542")


#    Catalogs = UUID("cf4abea6-37b2-11d4-940f-008048da11f9")


@unique
class MetaDataObjectTypes(StrEnum):
    Document = "Document"
    Catalog = "Reference"
    Field = "Fld"
    Enum = "Enum"


class Element(ABC):
    _name: str
    _table: str

    def __str__(self) -> str:
        return self._table

    def __repr__(self) -> str:
        return self._name


@final
class Document(Element):
    _prop: dict[str, str]

    def __init__(self, meta: list, /) -> None:
        self._name = meta[1][9][1][2]
        self._table = names[meta[1][9][1][1][2]]
        self._prop = frozendict({v[0][1][1][1][2]: names[v[0][1][1][1][1][2]] for v in iter(meta[5][2:])})

    def __getattr__(self, item) -> str:
        return self._prop[item]


@final
class Enum(Element):
    _prop: dict[str, str]

    def __init__(self, meta: list, /) -> None:
        self._name = meta[1][5][1][2]
        self._table = names[meta[1][5][1][1][2]]
        self._prop = frozendict({v[0][1][2]: v[0][1][1][2] for v in iter(meta[6][2:])})

    def __getattr__(self, item) -> str:
        return self._prop[item]

    def json(self, *, field_name_for_name: str = 'name', field_name_for_uid: str = 'uid') -> bytes:
        return orjson.dumps([{field_name_for_name: k, field_name_for_uid: v} for k, v in iter(self._prop.items())])


with files(engine, "Params") as params:  #

    names = {
        v[0]: f"_{v[1]}{v[2]}" for v in iter(params.send('DBNames')[1][0:])
        if isinstance(v, list) and v and len(v) == 3 and isinstance(v[0], UUID) and v[0].int
           and v[1] in MetaDataObjectTypes}

metadata: dict[PurePosixPath, Element] = {}

with files(engine, "Config") as config:  #

    configuration = {
        MetaDataGroup(v[0]): {
            MetaDataTypes(v[0]): [
                config.send(v) for v in iter(v[2:])
            ] for v in iter(v[1][1][3:]) if v[0] in MetaDataTypes
        } for v in iter(config.send(config.send("root")[1]))
        if isinstance(v, list) and v and len(v) == 2 and isinstance(v[0], UUID)
           and v[0] in MetaDataGroup and v[0].int and isinstance(v[1], list) and v[1]}

    for el in configuration[MetaDataGroup.Main][MetaDataTypes.Documents]:
        metadata[PurePosixPath('Документ', repr(el))] = (el := Document(el))

    for el in configuration[MetaDataGroup.Main][MetaDataTypes.Enums]:
        metadata[PurePosixPath('Перечисление', repr(el))] = (el := Enum(el))

    del el

pass
