import speech_recognition as sr
import autogen
import requests
import os
import config
from serpapi import GoogleSearch
from dotenv import load_dotenv


r = sr.Recognizer()


def record_text():
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
    f = open("output.txt", "a")
    f.write(text)
    f.write("\n")
    f.close()
    return


if __name__ == "__main__":
    config_list = {
        "model": config.model,
        "base_url": config.base_url,
        "api_key": os.getenv("GROQ_API_KEY"),
    }

    manager_agent = autogen.UserProxyAgent(
        name="Manager_Agent",
        system_message="You return information I give you and remember data you provided",
        llm_config={"config_list": [config_list]},
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "results", "use_docker": False},
        is_termination_msg=lambda msg: msg.get("content") is not None
        and "TERMINATE" in msg["content"],
    )

    helper_agent = autogen.ConversableAgent(
        name="Helper_Agent",
        system_message="You are responsible for answering personal questions that have predefined answers. \
            For example: Where are you? When you will be online?\
                Also You are responsible for assigning meetings, reminders, tasks given a request and data about the future plans \
            You need to ask for this information, such as time, place, title, summary if it is not provided",
        llm_config={"config_list": [config_list]},
        code_execution_config=False,
        # max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
    )

    @manager_agent.register_for_execution()
    @helper_agent.register_for_llm(description="Some description")
    def create_task():
        pass

    @manager_agent.register_for_execution()
    @helper_agent.register_for_llm(description="Some description")
    def get_answer():
        pass

    manager_agent.initiate_chat(helper_agent, message="Instance message")

    while 1:
        text = record_text()
        output_text(text)

        print("Wrote text")
