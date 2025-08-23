import requests
import sounddevice as sd
import numpy as np
import io
import wave
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import threading
import queue
import re

# 定数
VOICEVOX_URL = "http://localhost:50021"
SPEAKER_ID = 89  # VOICEVOXのスピーカーID

# スレッド間でデータをやり取りするためのキュー
text_chunk_queue = queue.Queue()
audio_data_queue = queue.Queue()


def text_generator_thread(prompt: str):
    """
    (スレッド1) Gemma APIからテキストをストリーミングで取得し、句読点で区切ってキューに入れる
    """
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        model_names = ["gemini-2.5-flash-lite","gemma-3n-e2b-it"]

        context = "# Do not speak about this section. Just attention.\n\nDo not use markdown, emojis, or line breaks. If there is something you do not know or cannot do, answer honestly by saying so. Do not use English. When English words must appear, write them in katakana.\n\n#Below is the input from the user.\n\n"
        full_prompt = context + prompt

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)],
            ),
        ]

        sentence_buffer = ""
        # 区切り文字の正規表現（。と改行）
        delimiters = r"。"

        print("Gemma: ", end="", flush=True)

        stream = None
        for model in model_names:
            try:
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                )
                print("Using Model:",model)
                break
            except:
                continue

        for chunk in stream:
            if chunk.text:
                sentence_buffer += chunk.text
            print(chunk.text, end="", flush=True)

            while True:
                # バッファ内の句点を探す
                matches = [m.end() for m in re.finditer(delimiters, sentence_buffer)]
                if not matches:
                    break  # 句点が無ければ次のチャンク待ち

                # 50文字に最も近い句点を探す
                closest = min(matches, key=lambda x: abs(x - 50))

                # バッファ長が50文字以上、または句点が近い位置にある場合に分割
                if len(sentence_buffer) >= 50 or abs(closest - 50) <= 10:
                    split_point = closest
                    sentence = sentence_buffer[:split_point]
                    sentence_buffer = sentence_buffer[split_point:]
                    if sentence.strip():
                        text_chunk_queue.put(sentence)
                else:
                    break



        # ストリーム終了後、バッファに残ったテキストをキューに入れる
        if sentence_buffer.strip():
            text_chunk_queue.put(sentence_buffer)

    except Exception as e:
        print(f"\n[エラー] テキスト生成中にエラーが発生しました: {e}")
    finally:
        # 処理終了の目印としてNoneをキューに入れる
        text_chunk_queue.put(None)
        print("\n--- テキスト生成完了 ---")


def speech_synthesizer_thread():
    """
    (スレッド2) テキストチャンクをVOICEVOXで音声データに合成し、キューに入れる
    """
    while True:
        text = text_chunk_queue.get()
        if text is None:  # 終了シグナルを受け取ったらループを抜ける
            audio_data_queue.put(None)  # 次のスレッドに終了を伝える
            break

        try:
            # 1. 音声合成用のクエリを作成
            params = {"text": text, "speaker": SPEAKER_ID}
            response_query = requests.post(
                f"{VOICEVOX_URL}/audio_query", params=params, timeout=10
            )
            response_query.raise_for_status()
            audio_query_data = response_query.json()

            # 2. クエリを元に音声データを生成
            response_synthesis = requests.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": SPEAKER_ID},
                json=audio_query_data,  # data= ではなく json= を使うのが推奨
                timeout=10,
            )
            response_synthesis.raise_for_status()

            # 3. 音声データをキューに入れる
            audio_data_queue.put(response_synthesis.content)

        except requests.exceptions.RequestException as e:
            print(f"\n[エラー] VOICEVOXエンジンに接続できませんでした: {e}")
            # エラーが起きても後続の処理は継続
        except Exception as e:
            print(f"\n[エラー] 音声合成中に予期せぬエラーが発生しました: {e}")

    print("--- 音声合成完了 ---")


def audio_player_thread():
    """
    (スレッド3) キューから音声データを取り出して再生する
    """
    try:
        while True:
            audio_content = audio_data_queue.get()
            if audio_content is None:  # 終了シグナルを受け取ったらループを抜ける
                break

            # メモリ上でWAVデータを扱う
            with io.BytesIO(audio_content) as wav_file:
                with wave.open(wav_file, "rb") as wf:
                    samplerate = wf.getframerate()
                    data = wf.readframes(wf.getnframes())
                    audio_array = np.frombuffer(data, dtype=np.int16)

            # 音声を再生し、終わるまで待つ
            sd.play(audio_array, samplerate)
            sd.wait()

    except Exception as e:
        print(f"\n[エラー] 音声再生中にエラーが発生しました: {e}")
    finally:
        print("--- 音声再生完了 ---")


def main():
    """
    メイン処理。ユーザーからの入力を受け付け、各スレッドを起動する
    """
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("環境変数 GEMINI_API_KEY が設定されていません。")
        return

    print("会話を開始します。(終了するには 'exit' または 'quit' と入力)")
    while True:
        try:
            prompt = input("You: ")
            if prompt.lower() in ["exit", "quit", "終了"]:
                break

            # 各スレッドを準備して開始
            producer = threading.Thread(target=text_generator_thread, args=(prompt,))
            synthesizer = threading.Thread(target=speech_synthesizer_thread)
            player = threading.Thread(target=audio_player_thread)

            producer.start()
            synthesizer.start()
            player.start()

            # すべてのスレッドが終了するのを待つ
            producer.join()
            synthesizer.join()
            player.join()

            print("\n次の質問をどうぞ。")

        except (KeyboardInterrupt, EOFError):
            print("\nアプリケーションを終了します。")
            break


if __name__ == "__main__":
    main()
