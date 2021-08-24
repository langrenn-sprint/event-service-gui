"""Module for deltakere service."""
import logging
from typing import Any, List


class DeltakereService:
    """Class representing deltakere service."""

    async def get_all_deltakere(self, db: Any) -> List:
        """Get all deltakere function."""
        deltakere = []
        cursor = db.deltakere_collection.find()
        for document in await cursor.to_list(length=2000):
            deltakere.append(document)
            logging.debug(document)
        return deltakere

    async def get_deltaker_by_startnr(self, db: Any, startnummer: str) -> dict:
        """Get deltaker function."""
        result = await db.deltakere_collection.find_one({"Startnr": startnummer})
        return result

    async def get_deltakere_by_klubb(self, db: Any, klubb: str) -> List:
        """Get all deltakere function."""
        deltakere = []
        myquery = "^" + klubb
        cursor = db.deltakere_collection.find({"Klubb": {"$regex": myquery}})
        for document in await cursor.to_list(length=100):
            deltakere.append(document)
            logging.debug(document)
        return deltakere

    async def get_deltakere_by_lopsklasse(self, db: Any, klasse: str) -> List:
        """Get all deltakere function."""
        deltakere = []
        cursor = db.deltakere_collection.find({"Løpsklasse": klasse})
        for document in await cursor.to_list(length=100):
            deltakere.append(document)
            logging.debug(document)
        return deltakere

    async def get_deltakere_by_arsklasse(self, db: Any, klasse: str) -> List:
        """Get all deltakere function."""
        deltakere = []
        cursor = db.deltakere_collection.find({"ÅrsKlasse": klasse})
        for document in await cursor.to_list(length=100):
            deltakere.append(document)
            logging.debug(document)
        return deltakere

    async def create_deltakere(self, db: Any, body: Any) -> int:
        """Create deltakere function. Delete existing deltakere, if any."""
        returncode = 201
        collist = await db.list_collection_names()
        logging.debug(collist)
        if "deltakere_collection" in collist:
            returncode = 202
            result = await db.deltakere_collection.delete_many({})
            logging.debug(result)

        result = await db.deltakere_collection.insert_many(body)
        logging.debug("inserted %d docs" % (len(result.inserted_ids),))
        return returncode
