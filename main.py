import speech_recognition as sr
import autogen
import requests
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
    while 1:
        text = record_text()
        output_text(text)

        print("Wrote text")
