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


def record_audio(seconds):
    CHUNK = 4096
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = seconds
    WAVE_OUTPUT_FILENAME = "output.wav"

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

    wf = wave.open(WAVE_OUTPUT_FILENAME, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()


def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        # r.pause_threshold = 5
        r.adjust_for_ambient_noise(source, duration=1)
        print("何か話してください...")
        audio = r.listen(source)

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


def play_audio(text, file):
    tts = gTTS(text, lang="ja")
    tts.save(file)
    audio = AudioSegment.from_file(file)
    play(audio)
    os.remove(file)


if __name__ == "__main__":
    load_dotenv("../.env")
    # 発話用の音声ファイル
    audio_file = "/var/tmp/result.mp3"
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
        record_audio(5)

        # 音声をテキストに変換
        text = recognize_speech()
        print(f"You：{text}")

        if text:
            # ChatGPTにテキストを送信してレスポンスを取得
            answer = ask_gpt(text, messages)
            print(f"Genie：{answer}")

            # レスポンスを音声で発話
            play_audio(answer, audio_file)

            if answer.lower() == "終わりましょう":
                messages.clear()
                print(messages)
                messages.append(system_content)
                continue
