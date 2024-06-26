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
from gtts import gTTS
import threading
import pygame
import time
from pathlib import Path
from io import BytesIO



lock = threading.Lock()
semaphore = threading.Semaphore(1)

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
    # Acquire the semaphore before accessing the shared resource
    semaphore.acquire()
    try:
        # Append the text to the file
        with open("output_final.txt", "a", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")

        # Convert the text to speech and save it to an in-memory bytes buffer
        language = "en"
        myobj = gTTS(text=text, lang=language, slow=False)
        audio_fp = BytesIO()
        myobj.write_to_fp(audio_fp)
        audio_fp.seek(0)

        # Initialize pygame mixer
        pygame.mixer.init()

        # Load the audio data from the in-memory bytes buffer
        pygame.mixer.music.load(audio_fp, 'mp3')
        pygame.mixer.music.play()

        # Wait for the playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        # Always release the semaphore after accessing the shared resource
        semaphore.release()




if __name__ == "__main__":

    class GenerateAnswer(dspy.Signature):
        """With the provided context answer the question about person"""

        context = dspy.InputField(desc="Information about person.")
        question = dspy.InputField()

        answer = dspy.OutputField(
            desc="Don't include reasoning and context. Just short answer"
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
                embedding_function=self.huggingface_ef
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

    rag_model = dspy.GROQ(model=config.model, api_key=os.environ.get("GROQ_API_KEY"))
    dspy.settings.configure(lm=rag_model)

    config_list = {
        "model": config.model,
        "base_url": config.base_url,
        "api_key": os.getenv("GROQ_API_KEY"),
        "temperature": 0
    }

    manager_agent = autogen.UserProxyAgent(
        name="Manager_Agent",
        system_message="You are User proxy. The person who calls",
        llm_config={"config_list": [config_list]},
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "results", "use_docker": False},
        is_termination_msg=lambda msg: msg.get("content") is not None
        and "TERMINATE" in msg["content"],
    )

    helper_agent = autogen.ConversableAgent(
        name="Helper_Agent",
        system_message="You are human with no memory. All information you can get \
              from your past life you can get from answer_questions_tool. \
              You get human input and answer questions using knowledge database or do certain actions.\
                If at the end of the message you receive TERMINATE AGENT CONVERSATION 200 write TERMINATE",
        llm_config={"config_list": [config_list]},
        code_execution_config=False,
        # max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
    )

    def create_event(
        summary: Annotated[str, "Summary of the event or how should it be called"],
        location: Annotated[str, "Location of the event"],
        start: Annotated[
            str,
            "Start time of the event. Has to be in this format: \
                                  yyyy-mm-ddThh:mm:ss+02:00 \
                                  where y is for year, m for month, d for day, h for hour, m for minute \
                                  s for second",
        ],
        end: Annotated[
            str,
            "End time of the event. Has to be in this format: \
                                  yyyy-mm-ddThh:mm:ss+02:00 \
                                  where y is for year, m for month, d for day, h for hour, m for minute \
                                  s for second",
        ]
    ) -> str:
        """Tool for Helper Agent that creates event in Google Calendar

        Returns:
            str: information about new added event
        """
        result = gcalendar.create_event(
            summary=summary,
            location=location,
            start=start,
            end=end,
        )

        with open("output_agents.txt", "w", encoding="utf-8") as file:
            file.write(result["text"])

        if result["code"] == 200:
            return "TERMINATE AGENT CONVERSATION 200"
        else:
            return result["text"]

    def get_events() -> str:
        """Tool for Helper Agent that gets events from Google Calendar

        Returns:
            str: information about existing events
        """
        result = gcalendar.get_events()

        with open("output_agents.txt", "w", encoding="utf-8") as file:
            file.write(result["text"])

        if result["code"] == 200:
            return "TERMINATE AGENT CONVERSATION 200"

    def get_answer(question: Annotated[str, "Question"]) -> str:
        """Tool for Helper Agent that gets personal predefined questions

        Returns:
            str: answer about predefined question
        """
        thread = threading.Thread(target=output_text, args=("Searching for the answer in predefined questions",))
        thread.start()
        thread.join()  

        rag = RAG()

        pred = rag(question)

        print(f"Question: {question}")
        print(f"Predicted Answer: {pred.answer}")
        with open("output_agents.txt", "w", encoding="utf-8") as file:
            file.write(pred.answer)

        return "TERMINATE AGENT CONVERSATION 200"

    def get_human_input(error: Annotated[str, "error and suggestion for additional arguments to fix an issue."]) -> str:
        """Get additional clarification from human for function parameter
        Returns:
            str: additional clarification from human
        """
        print("Error: ", error)
        thread = threading.Thread(target=output_text, args=(error,))
        thread.start()
        thread.join()  
        text = record_text()
        return text

    def get_current_datetime() -> str:
        """Function to get current datetime

        Returns:
            str: current datetime
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    autogen.register_function(
        create_event,
        caller=helper_agent,
        executor=manager_agent,
        name="calendar_create_tool",
        description="Tool that helps to create new event in calendar. \
             This shoud be used when a user wants to create new event \
                  If parameters aren't provided ask human for additional input",
    )
    autogen.register_function(
        get_events,
        caller=helper_agent,
        executor=manager_agent,
        name="calendar_read_tool",
        description="Tool that helps to get list of future events from Google calendar \
            This should be used when a user wants to get future events from Google calendar",
    )
    autogen.register_function(
        get_answer,
        caller=helper_agent,
        executor=manager_agent,
        name="answer_questions_tool",
        description="Tool that answers questions. \
        This should be used when you are passed with some question that begins with who what when where",
    )
    autogen.register_function(
        get_human_input,
        caller=helper_agent,
        executor=manager_agent,
        name="human_input_tool",
        description="Tool that helps to additional arguments",
    )
    autogen.register_function(
        get_current_datetime,
        caller=helper_agent,
        executor=manager_agent,
        name="get_current_time_tool",
        description="Tool to use if you need to know current time.\
             Use this tool only if you need to know what time is right now ",
    )

    while 1:
        text = record_text()
        question = "Question: " + text
        thread = threading.Thread(target=output_text, args=(question,))
        thread.start()
        thread.join()  

        manager_agent.initiate_chat(helper_agent, message=text)

        answer = ""
        with open("output_agents.txt", "r", encoding="utf-8") as file:
            answer = file.read()
        print(answer)
        answer = "Answer: " + answer
        thread = threading.Thread(target=output_text, args=(answer,))
        thread.start()
        thread.join() 

        print("Wrote text")
