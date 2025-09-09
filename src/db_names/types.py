from pathlib import PurePosixPath
from typing import Union

from sqlalchemy.util import immutabledict

from .models import MetaParserTableDocument, MetaParserValuesEnum

MetaParser = Union[MetaParserTableDocument, MetaParserValuesEnum]
MetaData = immutabledict[PurePosixPath, MetaParser]