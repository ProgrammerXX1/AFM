from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams

WEAVIATE_CLIENT = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False
    )
)
