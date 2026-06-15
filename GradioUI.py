import gradio as gr

css = """
.header-text { text-align: center; margin-bottom: 20px; }
.status-bar { background-color: #f0f2f5; border-radius: 5px; padding: 10px; font-size: 14px; color: #555; }
"""

def create_ui(controller):
    with gr.Blocks(title="智能语音聊天助手") as demo:
        gr.Markdown("# 🎤 智能语音聊天助手", elem_classes="header-text")
        gr.Markdown("点击下方按钮开始录音，点击确认后系统会自动处理")

        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=400
                )
                status_output = gr.Textbox(
                        label="系统状态",
                        value="准备就绪",
                        interactive=False,
                        elem_classes="status-bar"
                    )

            with gr.Column(scale=1):
                with gr.Row(scale=1):                   
                    audio_input = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        label="点击录音"
                    )
                with gr.Row(scale=1):
                    submit_btn = gr.Button("确认", variant="primary")
                with gr.Row(scale=1):
                    text_input = gr.Textbox(
                        label="文本输入（调试）",
                        placeholder="在此输入文字...",
                        submit_btn=True,
                )
                with gr.Row(scale=1):
                    audio_output = gr.Audio(
                        label="语音回复",
                        interactive=False,
                        autoplay=True,
                    )
                                        

        submit_btn.click(
            fn=controller.handle_interaction,
            inputs=[audio_input, chatbot],
            outputs=[chatbot, status_output, audio_output]
        )

        text_input.submit(
            fn=controller.handle_interaction,
            inputs=[audio_input, text_input, chatbot],
            outputs=[chatbot, status_output, text_input, audio_output]
        )

    return demo