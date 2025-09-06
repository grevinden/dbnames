from contextlib import contextmanager
from enum import Enum, unique, StrEnum
from typing import Literal, cast, Generator
from uuid import UUID

import bom_decompressor
import curly_array
import sqlmodel
from pydantic import BaseModel, RootModel, Field, AliasPath
from sqlalchemy import create_engine, Engine, ScalarResult, column, table
from sqlmodel import Session


# noinspection PyDataclass
class DBName(BaseModel, frozen=True):
    uid: UUID = Field(validation_alias=AliasPath("root", 0))
    name: str = Field(validation_alias=AliasPath("root", 1))
    id: int = Field(validation_alias=AliasPath("root", 2))


engine = create_engine(
    "mssql+pyodbc://sa:yDeapxJXEvtWCLh8uGm4KA@1c-sql.delta.local:1433/processing"
    "?" "driver=ODBC+DRIVER+18+FOR+SQL+SERVER"
    "&" "TrustServerCertificate=Yes"
    , echo=True)


class Document(BaseModel): ...


class Metadata(BaseModel):
    Documents: dict[str, Document]


# noinspection PyShadowingNames,SpellCheckingInspection
@contextmanager
def files(
        engine: Engine, tname: Literal["Params", "Config"], *, schema: str = "dbo"
) -> Generator[Generator[curly_array.NestedCurlyArray, str | UUID, None]]:  #

    with Session(engine, autocommit=False) as session:
        def _():
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

        # @formatter:off
        gen = _();del _;next(gen);yield gen;gen.close();del gen
        # @formatter:on

    del session


@unique
class MetaDataGroup(Enum):
    Main = UUID('9fcd25a0-4822-11d4-9414-008048da11f9')


@unique
class MetaDataTypes(Enum):
    Documents = UUID("061d872a-5787-460e-95ac-ed74ea3a3e84")
    Catalogs = UUID("cf4abea6-37b2-11d4-940f-008048da11f9")


@unique
class MetaDataObjectTypes(StrEnum):
    Document = "Document"
    Catalog = "Reference"


with files(engine, "Params") as params:  #

    names = RootModel[dict[UUID, DBName]].model_validate({
        v[0]: {"root": v} for v in iter(params.send('DBNames')[1][0:])
        if isinstance(v, list) and v and len(v) == 3 and isinstance(v[0], UUID) and v[0].int
           and v[1] in MetaDataObjectTypes
    }).root

with files(engine, "Config") as config:  #

    configuration = {
        MetaDataGroup(v[0]): {
            MetaDataTypes(v[0]): {
                names[cast(UUID, v)]: config.send(v)[1] for v in iter(v[2:])
            } for v in iter(v[1][1][3:]) if v[0] in MetaDataTypes
        } for v in iter(config.send(config.send("root")[1]))
        if isinstance(v, list) and v and len(v) == 2 and isinstance(v[0], UUID)
           and v[0] in MetaDataGroup and v[0].int and isinstance(v[1], list) and v[1]}

pass
