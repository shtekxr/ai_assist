import os
import tempfile
import time
import wave

import httpx
import pyaudio
import keyboard
import pyautogui
import pyperclip
from vosk import Model, KaldiRecognizer
from dotenv import load_dotenv
from groq import Groq, DefaultHttpxClient
from g4f.client import Client
load_dotenv()







HTTP_PROXY = os.environ.get("HTTP_PROXY")

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
    http_client=DefaultHttpxClient(
        proxies=HTTP_PROXY,
        transport=httpx.HTTPTransport(local_address="0.0.0.0")
    )
)

os.environ['HTTP_PROXY'] = f'{HTTP_PROXY}'

gpt = Client(
    proxies=HTTP_PROXY
)


def record_audio(sample_rate=48000, channels=1, chunk=1024):
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk,
    )

    print("Нажмите и удерживайте кнопку PAUSE, чтобы начать запись...")
    frames = []
    keyboard.wait("pause")  # Ожидание нажатия кнопки PAUSE
    print("Запись... (Отпустите PAUSE, чтобы остановить)")
    while keyboard.is_pressed("pause"):
        data = stream.read(chunk)
        frames.append(data)
    print("Запись завершена.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    return frames, sample_rate


def save_audio(frames, sample_rate):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        wf = wave.open(temp_audio.name, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return temp_audio.name


def transcribe_audio(audio_file_path):
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model="whisper-large-v3",
                prompt=""" """,
                response_format="text",
                language="ru",
            )
        return transcription
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        return None


def gpt_from_audio(transcription):
    # try:
    #     text_by_gpt = client.chat.completions.create(
    #         messages=[
    #             {
    #                 'role': 'system',
    #                 'content': 'Ты помощник на python'
    #             },
    #             {
    #                 'role': 'user',
    #                 # 'content': f'Пиши кратко и только по делу. {str(transcription)}'
    #                 'content': f'Пиши только код на Python, и ни единого слова кроме кода. {str(transcription)}'
    #             }
    #         ],
    #         model="llama3-70b-8192",
    #     )
    #     return text_by_gpt
    # except Exception as e:
    #     print(f"Произошла ошибка: {str(e)}")
    #     return None

    try:
        text_by_gpt = gpt.chat.completions.create(
            messages=[
                {
                    'role': 'system',
                    'content': 'Ты помощник на python'
                },
                {
                    'role': 'user',
                    'content': f'Пиши только код на Python, и ни единого слова кроме кода, '
                               f'даже цитату делать нельзя. {str(transcription)}'
                }
            ],
            model='gpt-4o',
        )

        return text_by_gpt
    except:
        return None


def copy_transcription_to_clipboard(text):
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def main():
    while True:
        # Запись аудио
        frames, sample_rate = record_audio()

        # Сохранение аудио во временный файл
        temp_audio_file = save_audio(frames, sample_rate)

        # Транскрибация аудио
        print("Транскрибация...")
        transcription = transcribe_audio(temp_audio_file)

        # Копирование транскрипции в буфер обмена
        if transcription:
            print("\nТранскрипция:")
            print(transcription)
            text_by_gpt = gpt_from_audio(transcription)
            text_by_gpt = str(text_by_gpt.choices[0].message.content)
            print(text_by_gpt)
            if text_by_gpt:
                print("Копирование транскрипции в буфер обмена...")

                copy_transcription_to_clipboard(str(text_by_gpt
                                                .replace('\\n', '\n').replace('```', '')
                                                .replace('\\', '')).replace('python', ''))
                print("Транскрипция скопирована в буфер обмена и вставлена в приложение.")

        else:
            print("Транскрибация не удалась.")

        # Удаление временного файла
        os.unlink(temp_audio_file)
        print("\nГотов к следующей записи. Нажмите PAUSE для начала.")






if __name__ == "__main__":
    main()


