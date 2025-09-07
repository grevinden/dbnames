from enum import unique, Enum, StrEnum
from uuid import UUID


@unique
class MetaDataGroup(Enum):
    Main = UUID('9fcd25a0-4822-11d4-9414-008048da11f9')


@unique
class MetaDataTypes(Enum):
    Documents = UUID("061d872a-5787-460e-95ac-ed74ea3a3e84")
    Enums = UUID("f6a80749-5ad7-400b-8519-39dc5dff2542")


@unique
class MetaDataObjectTypes(StrEnum):
    Document = "Document"
    Catalog = "Reference"
    Field = "Fld"
    Enum = "Enum"