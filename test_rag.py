import speech_recognition as sr
import autogen
import dspy
from dspy.retrieve.chromadb_rm import ChromadbRM
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from typing_extensions import Annotated
import os
import config
from dotenv import load_dotenv
import gcalendar
from datetime import datetime

class GenerateAnswer(dspy.Signature):
    """With the provided context answer the question about person.
        You have to be gentle and nice"""

    context = dspy.InputField(desc="Information about person.")
    question = dspy.InputField()

    answer = dspy.OutputField(
        desc="Full answer and short with finished answer. Don't include reasoning and question in you answer"
    )

class RAG(dspy.Module):
    def __init__(self):
        super().__init__()
        self.huggingface_ef = embedding_functions.HuggingFaceEmbeddingFunction(
            api_key=os.getenv("HUGGING_FACE_API_KEY"),
            model_name=os.getenv("RETREIVAL_MODEL_NAME"),
        )
        self.retrieve = ChromadbRM(
            "rag",
            persist_directory=os.path.join("rag"),
            embedding_function=self.huggingface_ef,
            k=2,
        )
        self.generate_answer = dspy.ChainOfThought(GenerateAnswer)

    def forward(self, question):
        context = self.retrieve(question)
        prediction = self.generate_answer(context=context, question=question)
        return dspy.Prediction(context=context, answer=prediction.answer)


client = chromadb.PersistentClient("rag")
collection = client.get_or_create_collection(
    name="rag"
)  # create collection if it doesn't exist

rag_model = dspy.GROQ(model=config.model, api_key=os.environ.get("GROQ_API_KEY"))
dspy.settings.configure(lm=rag_model)
rag = RAG()
question = str(input("Question: "))
print(question)
pred = rag(question)

print(f"Question: {question}")
print(f"Predicted Answer: {pred.answer}")
with open("output_agents_test.txt", "w", encoding="utf-8") as file:
    file.write(pred.answer)