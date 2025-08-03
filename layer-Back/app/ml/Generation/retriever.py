from typing import List, Dict
from weaviate.collections.classes.filters import Filter
from app.core.weaviate_client import client as weaviate_client

def get_chunks_by_case_id(case_id: int) -> List[Dict]:
    if not weaviate_client.is_connected():
        weaviate_client.connect()

    collection = weaviate_client.collections.get("Document")

    where_filter = Filter.by_property("case_id").equal(case_id)

    results = collection.query.fetch_objects(
        filters=where_filter,
        limit=2000  # если чанков много, увеличить лимит
    )

    return [obj.properties for obj in results.objects]
