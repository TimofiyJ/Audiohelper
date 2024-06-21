from typing import List
import os
from llama_index.core import Document
import chromadb
import uuid
from chromadb import Collection
from sentence_transformers import SentenceTransformer
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from dotenv import load_dotenv

load_dotenv(override=True)


def insert_record(model: SentenceTransformer, collection: Collection, info: str):
    """Insert record into collection (vectordb)

    Args:
        model : model for encoding
        collection : target collection
        info : main information
    """
    query_vector = model.encode(info).tolist()

    collection.add(
        embeddings=[query_vector],
        documents=[info],
        metadatas=[{"metadata": "1"}],  # TODO: expand information in metadata
        ids=[str(uuid.uuid4())],
    )


def get_clean_documents(data_folder: List[str]):
    """Extract all text information from pdf files located in data folder.
    Clean the text for each document page and document as a whole.
    Append document text as plain text to text_list, then
    translate it to Document object
    Args:
        data_folder (list[str]): list of paths of all data

    Returns:
        list: Array of objects Document type
    """
    text_list = []

    for document_name in data_folder:
        print(document_name)
        try:
            with open("./data/" + document_name, "r", encoding="utf-8") as file:
                text_list.append(file.read())
        except Exception as e:
            print("Cant read file, error: ", e)

    documents = [Document(text=t) for t in text_list]

    return documents


def get_nodes(documents: List[Document]):
    """Perform semantic chunking on the documents and transform them to nodes
    Args:
        documents (list): list of objects Document type that are to be converted to Node type

    Returns:
        list: array of objects Node type
    """
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=HuggingFaceEmbedding(model_name=os.getenv("RETREIVAL_MODEL_NAME")),
    )

    nodes = splitter.get_nodes_from_documents(documents)

    return nodes


def load_data():
    """Gets clean data, transform it into documents and then into nodes,
    insert data into vectordb
    """
    documents = get_clean_documents(os.listdir(os.path.join("data")))
    nodes = get_nodes(documents)

    client = chromadb.PersistentClient(path="rag")

    collection = client.get_or_create_collection(
        "rag", metadata={"hnsw:space": "cosine"}
    )

    model = SentenceTransformer(os.getenv("RETREIVAL_MODEL_NAME"))

    for idx, line in enumerate(nodes):
        try:
            insert_record(
                model=model,
                collection=collection,
                info=line.text,
            )
        except Exception as e:
            with open("bad_lines.txt", "a") as errors_f:
                errors_f.write(f"{line} error is: {e}\n")


if __name__ == "__main__":
    load_data()