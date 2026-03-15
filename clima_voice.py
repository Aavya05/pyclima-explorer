from gtts import gTTS
import streamlit as st

def generate_story(year,month,stats):

    text = f"""
    Climate summary for {month} {year}.

    The global mean temperature was {round(stats["mean"],2)} degrees.

    The highest temperature recorded was {round(stats["max"],2)} degrees.

    The minimum temperature recorded was {round(stats["min"],2)} degrees.

    Climate anomaly analysis shows variations across regions
    indicating possible climate events.
    """

    return text


def speak_story(text):

    tts = gTTS(text)

    file = "climate_voice.mp3"

    tts.save(file)

    audio_file = open(file,"rb")

    st.audio(audio_file.read(),format="audio/mp3")