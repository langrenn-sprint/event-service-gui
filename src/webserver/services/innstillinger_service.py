"""Module for innstillinger service."""
import logging
from typing import Any, List


class InnstillingerService:
    """Class representing innstillinger service."""

    async def get_all_innstillinger(self, db: Any) -> List:
        """Get all innstillinger function."""
        innstillinger = []
        cursor = db.innstillinger_collection.find()
        for document in await cursor.to_list(length=2000):
            innstillinger.append(document)
            logging.debug(document)
        return innstillinger

    async def get_arrangor(self, db: Any) -> str:
        """Get one innstilling."""
        result = await db.innstillinger_collection.find_one({"Parameter": "Arrangør"})
        try:
            _arrangor = result["Verdi"]
        except Exception:
            _arrangor = ""
        logging.debug(_arrangor)

        return _arrangor

    async def get_dato(self, db: Any) -> str:
        """Get one innstilling."""
        result = await db.innstillinger_collection.find_one({"Parameter": "Dato"})
        try:
            _dato = result["Verdi"]
        except Exception:
            _dato = ""
        logging.debug(_dato)

        return _dato

    async def get_lopsnavn(self, db: Any) -> str:
        """Get one innstilling."""
        result = await db.innstillinger_collection.find_one({"Parameter": "Løpsnavn"})
        logging.debug(result)
        try:
            _lopsnavn = result["Verdi"]
        except Exception:
            _lopsnavn = ""

        logging.debug(_lopsnavn)

        return _lopsnavn

    async def get_lopsvarighet(self, db: Any) -> str:
        """Get one innstilling."""
        result = await db.innstillinger_collection.find_one(
            {"Parameter": "Løpsvarighet"}
        )
        logging.debug(result)
        try:
            _lopsvarighet = result["Verdi"]
        except Exception:
            _lopsvarighet = ""

        logging.debug(_lopsvarighet)

        return _lopsvarighet

    async def get_header_footer_info(self, db: Any) -> List:
        """Get innstillinger for header/footer - navn, dato, arrangør."""
        _retvalue = []
        _parameter = ""
        result = await db.innstillinger_collection.find_one({"Parameter": "Løpsnavn"})
        try:
            _parameter = result["Verdi"]
        except Exception:
            _parameter = ""
        logging.debug(_parameter)
        _retvalue.append(_parameter)
        result = await db.innstillinger_collection.find_one({"Parameter": "Arrangør"})
        try:
            _parameter = result["Verdi"]
        except Exception:
            _parameter = ""
        logging.debug(_parameter)
        _retvalue.append(_parameter)
        result = await db.innstillinger_collection.find_one({"Parameter": "Dato"})
        try:
            _parameter = result["Verdi"]
        except Exception:
            _parameter = ""
        logging.debug(_parameter)
        _retvalue.append(_parameter)

        return _retvalue

    async def create_innstillinger(self, db: Any, body: Any) -> int:
        """Create innstillinger function. Delete existing innstillinger, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        if "innstillinger_collection" in collist:
            returncode = 202
            result = await db.innstillinger_collection.delete_many({})
            logging.debug(result)

        result = await db.innstillinger_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))
        return returncode
