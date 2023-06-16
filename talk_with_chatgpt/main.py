import re
import wave
from dotenv import load_dotenv
import os

from gtts import gTTS
import speech_recognition as sr
import openai
from pydub import AudioSegment
from pydub.playback import play
import pyaudio


def record_audio(seconds, wave_file):
    CHUNK = 4096
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = seconds

    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
    )
    print("レコーディング中...")
    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("レコーディング完了!")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    wf = wave.open(wave_file, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()


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
    except sr.RequestError as e:
        print(f"エラーが発生しました。 {e}")


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


def play_audio(text, wave_file):
    tts = gTTS(text, lang="ja")
    tts.save(wave_file)
    audio = AudioSegment.from_file(wave_file)
    play(audio)


def remove_files(files):
    [os.remove(file) for file in files]


if __name__ == "__main__":
    INPUT_WAVE_FILE = "/var/tmp/input.wav"
    OUTPUT_WAVE_FILE = "/var/tmp/output.wav"

    load_dotenv("../.env")

    # .envにOPENAI_API_KEYを設定する
    openai.api_key = os.getenv("OPENAI_API_KEY")

    system_content = """
        あなたは私の相談相手です。
        あなたは「ごとーちゃん」と呼ばれています。
        アメリカのシリコンバレーで働くプロフェッショナルなエンジニアです。
    """
    system_context = {"role": "system", "content": system_content}

    messages = []
    messages.append(system_context)

    while True:
        # 音声を録音
        record_audio(5, INPUT_WAVE_FILE)

        # 音声をテキストに変換
        text = recognize_speech(INPUT_WAVE_FILE)
        print(f"You：{text}")

        if text:
            # ChatGPTにテキストを送信してレスポンスを取得
            answer = ask_gpt(text, messages)
            print(f"Genie：{answer}")

            # レスポンスを音声で発話
            play_audio(answer, OUTPUT_WAVE_FILE)

            if answer.lower() == "終わりましょう":
                messages.clear()
                print(messages)
                messages.append(system_content)
                remove_files([INPUT_WAVE_FILE, OUTPUT_WAVE_FILE])
                continue
