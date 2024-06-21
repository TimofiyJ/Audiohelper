from dspy.retrieve.chromadb_rm import ChromadbRM
import chromadb.utils.embedding_functions as embedding_functions
import os 

GROQ_API_KEY = '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'
SERP_API_KEY = '7857f0a848c6da89cbf2de4875e0ca70db1f22df37ccc92c022aa56f300dfb4c'
HUGGING_FACE_API_KEY = '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'
RETREIVAL_MODEL_NAME = 'BAAI/bge-large-en-v1.5'



huggingface_ef = embedding_functions.HuggingFaceEmbeddingFunction(
    api_key=HUGGING_FACE_API_KEY,
    model_name=RETREIVAL_MODEL_NAME
)
retrieve = ChromadbRM(
    "rag",
    persist_directory=os.path.join("rag"),
    embedding_function=huggingface_ef,
    k=2,
)


print(retrieve('what is you name?'))






