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

load_dotenv(override=True)


def record_text() -> str:
    while 1:
        try:
            with sr.Microphone() as source2:
                r.adjust_for_ambient_noise(source2, duration=0.2)

                audio2 = r.listen(source2)

                MyText = r.recognize_google(audio2)

                return MyText

        except sr.RequestError as e:
            print(f"Could not request results: {e}")

        except sr.UnknownValueError:
            print("Unknown value error")

    return


def output_text(text):
    f = open("output.txt", "a", encoding="utf-8")
    f.write(text)
    f.write("\n")
    f.close()
    return


if __name__ == "__main__":

    class GenerateAnswer(dspy.Signature):
        """With the provided context answer the question about person.
        You have to be gentle and nice"""

        context = dspy.InputField(
            desc="Information about person."
        )
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

    r = sr.Recognizer()

    client = chromadb.PersistentClient("rag")
    collection = client.get_or_create_collection(
        name="rag"
    )  # create collection if it doesn't exist

    rag_model = dspy.GROQ(
        model=config.model, api_key=os.environ.get("GROQ_API_KEY")
    )
    dspy.settings.configure(lm=rag_model)

    config_list = {
        "model": config.model,
        "base_url": config.base_url,
        "api_key": os.getenv("GROQ_API_KEY"),
    }

    manager_agent = autogen.UserProxyAgent(
        name="Manager_Agent",
        system_message="You are responsible for communication between user and other agents, also you execute code",
        llm_config={"config_list": [config_list]},
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "results", "use_docker": False},
        is_termination_msg=lambda msg: msg.get("content") is not None
        and "TERMINATE" in msg["content"],
    )

    helper_agent = autogen.ConversableAgent(
        name="Helper_Agent",
        system_message="You are responsible for answering personal questions that have predefined answers. \
            For example: Where are you? When you will be in town?\
                Also You are responsible for assigning meetings, reminders, tasks given a request and data about the future plans \
            You need to ask for this information, such as time, place, title, summary if it is not provided.\
                If at the end of the message you receive TERMINATE AGENT CONVERSATION 200 write TERMINATE",
        llm_config={"config_list": [config_list]},
        code_execution_config=False,
        max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
    )

    def create_event() -> str:
        """Tool for Helper Agent that creates event in Google Calendar

        Returns:
            str: information about new added event
        """
        result = gcalendar.create_event()

        with open("Event.txt", "w", encoding="utf-8") as file:
            file.write(result["text"])

        if result["code"] == 200:
            return "TERMINATE AGENT CONVERSATION 200"

    def get_events() -> str:
        """Tool for Helper Agent that gets events from Google Calendar

        Returns:
            str: information about existing events
        """
        result = gcalendar.get_events()

        with open("Event.txt", "w", encoding="utf-8") as file:
            file.write(result["text"])

        if result["code"] == 200:
            return "TERMINATE AGENT CONVERSATION 200"

    def get_answer(question: Annotated[str, "Personal predefined question"]) -> str:
        """Tool for Helper Agent that gets personal predefined questions

        Returns:
            str: answer about predefined question
        """
        rag = RAG()

        pred = rag(question)

        print(f"Question: {question}")
        print(f"Predicted Answer: {pred.answer}")

        return pred.answer

    autogen.register_function(
        create_event,
        caller=helper_agent,
        executor=manager_agent,
        name="calendar_create_tool",
        description="Tool that helps create new event in calendar. Use it when you have the word calendar",
    )
    autogen.register_function(
        get_events,
        caller=helper_agent,
        executor=manager_agent,
        name="calendar_read_tool",
        description="Tool that helps get events from calendar. Use it when you have the word calendar",
    )
    autogen.register_function(
        get_answer,
        caller=helper_agent,
        executor=manager_agent,
        name="predefined_questions_tool",
        description="Tool that helps get answers for personal predefined questions such as When, What, Who, Why",
    )

    while 1:
        text = record_text()
        question = "Question: " + text
        output_text(question)

        manager_agent.initiate_chat(helper_agent, message=text)

        answer = ""
        with open("Event.txt", "r", encoding="utf-8") as file:
            answer = file.read()
        print(answer)
        answer = "Answer: " + answer
        output_text(answer)

        print("Wrote text")
