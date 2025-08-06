import weaviate
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Property, DataType, Configure, ReferenceProperty

# Подключение
client = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False
    ),
    additional_config=AdditionalConfig(grpc=True, timeout=Timeout(init=10)),
    skip_init_checks=True
)

def drop_if_exists(name: str):
    if client.collections.exists(name):
        client.collections.delete(name)
        print(f"🧹 Старая коллекция '{name}' удалена.")

try:
    client.connect()

    # Удаляем все старые коллекции
    for name in ["Document","Chunk","Entity","Event","Evidence","Case","ActionItem"]:
        drop_if_exists(name)

    
    client.collections.create(
    name="Case",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="title", data_type=DataType.TEXT),
        Property(name="jurisdiction", data_type=DataType.TEXT),   # e.g. "KZ"
        Property(name="status", data_type=DataType.TEXT),          # intake/review/qualified/closed
        Property(name="createdAt", data_type=DataType.DATE),
        Property(name="updatedAt", data_type=DataType.DATE),
        Property(name="ownerUserId", data_type=DataType.TEXT, index_inverted=True),
    ]
)
    print("✅ Коллекция 'Case' создана.")

    client.collections.create(
    name="Document",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="docId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="userId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="title", data_type=DataType.TEXT),
        Property(name="type", data_type=DataType.TEXT),            # protocol/report/order/conclusion/...
        Property(name="sourceType", data_type=DataType.TEXT),      # upload/email/scan
        Property(name="sourcePath", data_type=DataType.TEXT),
        Property(name="mime", data_type=DataType.TEXT),
        Property(name="lang", data_type=DataType.TEXT),

        Property(name="fileSize", data_type=DataType.INT),
        Property(name="docHash", data_type=DataType.TEXT),         # заменяет старое 'hash'
        Property(name="checksum", data_type=DataType.TEXT),        # опционально, если отличаем

        Property(name="createdAt", data_type=DataType.DATE),
        Property(name="receivedAt", data_type=DataType.DATE),
        Property(name="pages", data_type=DataType.INT),
    ],
    references=[
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Document' создана.")

    client.collections.create(
    name="Chunk",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="chunkId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="docId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="pageStart", data_type=DataType.INT),
        Property(name="pageEnd", data_type=DataType.INT),

        Property(name="position", data_type=DataType.INT),         # порядковый номер в документе
        Property(name="chunkType", data_type=DataType.TEXT),       # header/body/table/footnote/appendix
        Property(name="chunkSubtype", data_type=DataType.TEXT),    # рапорт/протокол/постановление/...
        Property(name="section", data_type=DataType.TEXT),         # крупный раздел (если есть)
        Property(name="stage", data_type=DataType.TEXT),           # доследст./досудеб./суд

        Property(name="text", data_type=DataType.TEXT),
        Property(name="tokens", data_type=DataType.INT),

        Property(name="legalRefs", data_type=DataType.TEXT_ARRAY), # ссылки на нормы права, статьи
        Property(name="semanticHash", data_type=DataType.TEXT),
        Property(name="confidence", data_type=DataType.NUMBER),
        Property(name="salience", data_type=DataType.NUMBER),
    ],
    references=[
        ReferenceProperty(name="ofDocument", target_collection="Document"),
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Chunk' создана.")
 
    client.collections.create(
    name="Entity",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="entityId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="entityType", data_type=DataType.TEXT),      # PERSON/ORG/LAW_REF/ARTICLE/MONEY/...
        Property(name="name", data_type=DataType.TEXT),
        Property(name="normalized", data_type=DataType.TEXT),      # каноническая форма
        Property(name="source", data_type=DataType.TEXT),          # ner/spacy/regex/llm
        Property(name="extra", data_type=DataType.TEXT),           # JSON string (attrs)
        Property(name="confidence", data_type=DataType.NUMBER),
    ],
    references=[
        ReferenceProperty(name="mentionedIn", target_collection="Chunk"),
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Entity' создана.")

    client.collections.create(
    name="Event",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="eventId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="eventType", data_type=DataType.TEXT),       # search/seizure/transfer/payment/...
        Property(name="who", data_type=DataType.TEXT),
        Property(name="when", data_type=DataType.TEXT),            # исходный текст/дата
        Property(name="eventTimeStart", data_type=DataType.DATE),  # ISO при нормализации
        Property(name="eventTimeEnd", data_type=DataType.DATE),

        Property(name="where", data_type=DataType.TEXT),
        Property(name="amount", data_type=DataType.NUMBER),
        Property(name="currency", data_type=DataType.TEXT),

        Property(name="details", data_type=DataType.TEXT),
        Property(name="lawRefs", data_type=DataType.TEXT_ARRAY),   # статьи/нормы
        Property(name="confidence", data_type=DataType.NUMBER),
    ],
    references=[
        ReferenceProperty(name="entities", target_collection="Entity"),
        ReferenceProperty(name="evidenceFrom", target_collection="Chunk"),  # источники текста
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Event' создана.")

    client.collections.create(
    name="Evidence",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="evidenceId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="kind", data_type=DataType.TEXT),            # table/photo/scan/attachment/...
        Property(name="description", data_type=DataType.TEXT),
        Property(name="location", data_type=DataType.TEXT),        # путь/URI
        Property(name="pageRefs", data_type=DataType.INT_ARRAY),   # страницы источника
        Property(name="fileRef", data_type=DataType.TEXT),         # связанный файл (если отдельно)
        Property(name="hashRef", data_type=DataType.TEXT),
        Property(name="confidence", data_type=DataType.NUMBER),
    ],
    references=[
        ReferenceProperty(name="supportsEvent", target_collection="Event"),
        ReferenceProperty(name="supportsChunk", target_collection="Chunk"),
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Evidence' создана.")

    client.collections.create(
    name="ActionItem",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="actionId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="category", data_type=DataType.TEXT),        # evidence/request/analysis/...
        Property(name="text", data_type=DataType.TEXT),
        Property(name="priority", data_type=DataType.INT),         # 1..5
        Property(name="status", data_type=DataType.TEXT),          # open/in_progress/done
        Property(name="ownerUserId", data_type=DataType.TEXT),
        Property(name="dueDate", data_type=DataType.DATE),
    ],
    references=[
        ReferenceProperty(name="relatedEvent", target_collection="Event"),
        ReferenceProperty(name="relatedChunk", target_collection="Chunk"),
        ReferenceProperty(name="relatedEntity", target_collection="Entity"),
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'ActionItem' создана.")

    client.collections.create(
    name="Qualification",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="qualificationId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="charges", data_type=DataType.TEXT_ARRAY),   # стат. УК/УПК и т.п.
        Property(name="summary", data_type=DataType.TEXT),         # краткое резюме
        Property(name="rationale", data_type=DataType.TEXT),       # обоснование
        Property(name="confidence", data_type=DataType.NUMBER),
        Property(name="createdAt", data_type=DataType.DATE),
        Property(name="updatedAt", data_type=DataType.DATE),
    ],
    references=[
        ReferenceProperty(name="basedOnEvents", target_collection="Event"),
        ReferenceProperty(name="basedOnEvidence", target_collection="Evidence"),
        ReferenceProperty(name="inCase", target_collection="Case"),
    ]
)
    print("✅ Коллекция 'Qualification' создана.")

    client.collections.create(
    name="MissingItem",
    vectorizer_config=Configure.Vectorizer.text2vec_openai(),
    properties=[
        Property(name="missingId", data_type=DataType.TEXT, index_inverted=True),
        Property(name="caseId", data_type=DataType.TEXT, index_inverted=True),

        Property(name="itemType", data_type=DataType.TEXT),        # expert_conclusion/warrant/...
        Property(name="description", data_type=DataType.TEXT),
        Property(name="severity", data_type=DataType.INT),         # 1..5
        Property(name="status", data_type=DataType.TEXT),          # missing/requested/received
        Property(name="createdAt", data_type=DataType.DATE),
        Property(name="updatedAt", data_type=DataType.DATE),
    ],
    references=[
        ReferenceProperty(name="inCase", target_collection="Case"),
        ReferenceProperty(name="relatedEvent", target_collection="Event"),
    ]
)
    print("✅ Коллекция 'MissingItem' создана.")



except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    client.close()
    print("🔌 Соединение закрыто.")
