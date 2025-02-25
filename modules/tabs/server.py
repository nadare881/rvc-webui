import io
import json
import os

import gradio as gr
import requests
import soundfile as sf
import torch.multiprocessing as multiprocessing
from scipy.io.wavfile import write

from modules.shared import MODELS_DIR
from modules.ui import Tab
from server import app

proc = None

def server_options_ui(show_out_dir=True):
    with gr.Row().style(equal_height=False):
        with gr.Row():
            host = gr.Textbox(value="127.0.0.1", label="host")
            port = gr.Textbox(value="5001", label="port")
    with gr.Row().style(equal_height=False):
        with gr.Row():
            rvc_model_file = gr.Textbox(label="RVC model file path", value=os.path.join(
                                MODELS_DIR, "pretrained", "beta", "voras_sample_japanese.pth"
                            ))
    with gr.Row().style(equal_height=False):
        with gr.Row():
            input_voice_file = gr.Textbox(value="", label="input voice file path")
            speaker_id = gr.Number(
                value=0,
                label="speaker_id",
            )
    return (
        host,
        port,
        rvc_model_file,
        input_voice_file,
        speaker_id
    )

def run(**kwargs):
    app.run(**kwargs)

class Server(Tab):
    def title(self):
        return "Server(experimental)"

    def sort(self):
        return 6

    def ui(self, outlet):
        def start(host, port):
            if multiprocessing.get_start_method() == 'fork':
                multiprocessing.set_start_method('spawn', force=True)
            proc = multiprocessing.Process(target = run, kwargs = {'host': host, 'port': port})
            proc.start()
            yield "start server"

        def upload(host, port, rvc_model_file):
            file_names = {"rvc_model_file": rvc_model_file}
            res = requests.post(f"http://{host}:{port}/upload_model", json=file_names)
            yield res.text

        def convert(host, port, input_voice_file, speaker_id):
            params = {
                "speaker_id": speaker_id,
            }

            audio, sr = sf.read(input_voice_file)
            audio_buffer = io.BytesIO()
            write(audio_buffer, rate=sr, data=audio)
            json_buffer = io.BytesIO(json.dumps(params).encode('utf-8'))
            files = {
                "input_wav": audio_buffer,
                "params": json_buffer
            }
            res = requests.post(f"http://{host}:{port}/convert_sound", files=files)
            audio, sr = sf.read(io.BytesIO(res.content))
            yield "convert succeed", (sr, audio)

        with gr.Group():
            with gr.Box():
                with gr.Column():
                    (
                        host,
                        port,
                        rvc_model_file,
                        input_voice_file,
                        speaker_id,
                    ) = server_options_ui()

                    with gr.Row().style(equal_height=False):
                        with gr.Column():
                            status = gr.Textbox(value="", label="Status")
                            output = gr.Audio(label="Output", interactive=False)

                    with gr.Row():
                        start_button = gr.Button("Start server", variant="primary")
                        upload_button = gr.Button("Upload Model")
                        convert_button = gr.Button("Convert Voice")

        start_button.click(
            start,
            inputs=[
                host,
                port
            ],
            outputs=[status],
            queue=True,
        )
        upload_button.click(
            upload,
            inputs=[
                host,
                port,
                rvc_model_file
            ],
            outputs=[status],
            queue=True,
        )
        convert_button.click(
            convert,
            inputs=[
                host,
                port,
                input_voice_file,
                speaker_id
            ],
            outputs=[status, output],
            queue=True,
        )