import re
import wave
import os
import audioop
import pyaudio
from dotenv import load_dotenv
from gtts import gTTS
import speech_recognition as sr
import openai
from pydub import AudioSegment
from pydub.playback import play
import numpy as np


load_dotenv()


def record_audio(input_wave_file, silent_chunks=3):
    CHUNK = 4096
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    THRESHOLD = 50
    SILENT_CHUNKS = silent_chunks * RATE / CHUNK
    frames = []
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print("レコーディング中...")

    silent_chunk_count = 0
    while True:
        data = stream.read(CHUNK)
        rms = audioop.rms(data, 2)
        if rms < THRESHOLD:
            silent_chunk_count += 1
            if silent_chunk_count > SILENT_CHUNKS:
                break
        else:
            silent_chunk_count = 0
        frames.append(data)
    print("レコーディング完了!")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(input_wave_file, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))


def play_beep_sound():
    FREQUENCY = 220
    FORMAT = pyaudio.paInt32
    DURATION = 1.5
    CHANNELS = 1
    RATE = 44100
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    beep = (np.sin(2 * np.pi * np.arange(RATE * DURATION) * FREQUENCY / RATE)).astype(
        np.float32
    )

    stream.write(beep)
    stream.stop_stream()
    stream.close()
    p.terminate()


def recognize_speech(audio_file):
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)

    try:
        text = r.recognize_google(audio, language="ja-JP")
        clean_text = re.sub("( |　)+", "", text)  # type: ignore
        return clean_text
    except sr.UnknownValueError:
        print("聞き取れませんでした。もう一度喋ってください。")
        return None
    except sr.RequestError as e:
        print(f"エラーが発生しました。 {e}")
        return None


def ask_gpt(text, messages):
    messages.append({"role": "user", "content": text})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.8,
    )

    answer = re.sub("\n", "", response["choices"][0]["message"]["content"])  # type: ignore
    messages.append({"role": "assistant", "content": answer})

    return answer


def play_audio(text, output_wave_file):
    tts = gTTS(text, lang="ja")
    tts.save(output_wave_file)
    if os.path.exists(output_wave_file):
        audio = AudioSegment.from_file(output_wave_file)
        play(audio)


def remove_files(file_list):
    [os.remove(file) for file in file_list if os.path.exists(file)]


if __name__ == "__main__":
    INPUT_WAVE_FILE = "/var/tmp/input.wav"
    OUTPUT_WAVE_FILE = "/var/tmp/output.wav"
    openai.api_key = os.getenv("OPENAI_API_KEY")
    system_content = """
        あなたは私の相談相手です。
        あなたは「ごとーちゃん」と呼ばれています。
        アメリカのシリコンバレーで働くソフトウェアエンジニア兼SREです。
    """
    system_context = {"role": "system", "content": system_content}
    messages = []
    messages.append(system_context)

    while True:
        play_beep_sound()
        # 音声を録音
        record_audio(INPUT_WAVE_FILE)

        # 音声をテキストに変換
        text = recognize_speech(INPUT_WAVE_FILE)
        print(f"You：{text}")

        if text:
            # ChatGPTにテキストを送信してレスポンスを取得
            answer = ask_gpt(text, messages)
            print(f"Genie：{answer}")

            # レスポンスを音声で発話
            play_audio(answer, OUTPUT_WAVE_FILE)

            if answer == "終わりましょう":
                messages.clear()
                print(messages)
                messages.append(system_content)
                remove_files([INPUT_WAVE_FILE, OUTPUT_WAVE_FILE])
                continue
