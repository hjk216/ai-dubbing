import io
import os
import subprocess
import streamlit as st
import whisper
from pytube import YouTube
from pydub import AudioSegment
import pandas as pd
from elevenlabs.client import ElevenLabs
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
# import anthropic
from openai import OpenAI

# NOTE: Temp Turn off SSL verification
import ssl
ssl._create_default_https_context = ssl._create_unverified_context



def combine_video(video_filename, audio_filename):
    ffmpeg_extract_subclip(video_filename, 0, 60, targetname="cut_audio.mp4")
    output_filename = "output.mp4"
    command = ["ffmpeg", "-y", "-i", "cut_audio.mp4", "-i", audio_filename, "-c:v", "copy", "-c:a", "aac", output_filename]
    subprocess.run(command)
    return output_filename



def generate_dubs(text):
    filename = "output.mp3"

    client = ElevenLabs(
        api_key=st.secrets['xi_api_key']
    )

    audio_generator = client.generate(
        text=text,
        model='eleven_multilingual_v1'
    )

    audio = b''.join(audio_generator)
    
    audio_io = io.BytesIO(audio)
    insert_audio = AudioSegment.from_file(audio_io, format='mp3')
    insert_audio.export(filename, format="mp3")
    
    return filename



def shorten_audio(filename):
    filename = "cut_audio.mp4"

    audio = AudioSegment.from_file(filename)
    
    cut_audio = audio[:60 * 1000]

    cut_audio.export(filename, format="mp4")

    return filename



def generate_translation(original_text, destination_language):
    open_ai_client = OpenAI(api_key=st.secrets["open_ai_key"])

    prompt = (f"Please translate the following video transcript into {destination_language}. "
              f"Here is the transcript: {original_text}")

    response = open_ai_client.completions.create(model="gpt-3.5-turbo-instruct",
    prompt=prompt,
    max_tokens=900,
    temperature=0.5)

    translation = response.choices[0].text.strip()
    print(translation)

    return translation


# def generate_translation(original_text, destination_language):
#     prompt = (f"{anthropic.HUMAN_PROMPT} Please translate this video transcript into {destination_language}. You will get to the translation directly after I prompted 'the translation:'"
#               f"{anthropic.AI_PROMPT} Understood, I will get to the translation without any opening lines."
#               f"{anthropic.HUMAN_PROMPT} Great! this is the transcript: {original_text}; the translation:")

#     c = anthropic.Anthropic(api_key=st.secrets["claude_key"])

#     resp = c.completions.create(
#         prompt=f"{prompt} {anthropic.AI_PROMPT}",
#         stop_sequences=[anthropic.HUMAN_PROMPT],
#         model="claude-v1.3-100k",
#         max_tokens_to_sample=900,
#     )

#     print(resp.completion)

#     return resp.completion



st.title("AutoDubs 📺🎵")

link = st.text_input("Link to Youtube Video", key="link")

language = st.selectbox("Translate to", ("French", "German", "Hindi", "Italian", "Polish", "Portuguese", "Spanish"))

if st.button("Transcribe!"):
    print(f"downloading from link: {link}")

    model = whisper.load_model("base")

    yt = YouTube(link)

    if yt is not None:

        st.subheader(yt.title)
        st.image(yt.thumbnail_url)

        audio_name = st.caption("Downloading audio stream...")

        audio_streams = yt.streams.filter(only_audio=True)
        filename = audio_streams.first().download()

        if filename:
            filename = "cut_audio.mp4"
            audio_name.caption(filename)
            cut_audio = shorten_audio(filename)
            transcription = model.transcribe(cut_audio)

            print(transcription)

            if transcription:
                df = pd.DataFrame(transcription['segments'], columns=['start', 'end', 'text'])
                st.dataframe(df)

                dubbing_caption = st.caption("Generating translation...")
                translation = generate_translation(transcription['text'], language)

                dubbing_caption = st.caption("Begin dubbing...")

                dubs_audio = generate_dubs(translation)

                dubbing_caption.caption("Dubs generated! combining with the video...")

                video_streams = yt.streams.filter(only_video=True)
                video_filename = video_streams.first().download()

                if video_filename:
                    dubbing_caption.caption("Video downloaded! combining the video and the dubs...")
                    
                    output_filename = combine_video(video_filename, dubs_audio)
                    
                    if os.path.exists(output_filename):
                        dubbing_caption.caption("Video successfully dubbed! Enjoy! 😀")
                        st.video(output_filename)
