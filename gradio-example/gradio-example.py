import gradio as gr
import json
import os

def load_counts():
    if os.path.exists("counts.json"):
        with open("counts.json", "r") as f:
            counts = json.load(f)
    else:
        counts = {"video1_count": 0, "video2_count": 0}
    return counts

def save_counts(counts):
    with open("counts.json", "w") as f:
        json.dump(counts, f)

def create_demo(video1_path="robot_Example1.mp4", video2_path="robot_Example2.mp4"):
    def pick_video_1(prev_choice):
        counts = load_counts()
        if prev_choice == 1:
            return "video 1 chosen", prev_choice
        if prev_choice == 2:
            counts["video2_count"] -= 1
        counts["video1_count"] += 1
        save_counts(counts)
        return "video 1 chosen", 1

    def pick_video_2(prev_choice):
        counts = load_counts()
        if prev_choice == 2:
            return "video 2 chosen", prev_choice
        if prev_choice == 1:
            counts["video1_count"] -= 1
        counts["video2_count"] += 1
        save_counts(counts)
        return "video 2 chosen", 2

    with gr.Blocks() as demo:
        session_state = gr.State(0)
        gr.Markdown("## Select a Video")
        with gr.Row():
            with gr.Column():
                gr.Video(video1_path, label="Video 1")
            with gr.Column():
                gr.Video(video2_path, label="Video 2")
        with gr.Row():
            btn1 = gr.Button("Choose Video 1")
            btn2 = gr.Button("Choose Video 2")

        choice_display = gr.Textbox(label="Your choice", interactive=False)

        btn1.click(fn=pick_video_1, inputs=[session_state], outputs=[choice_display, session_state])
        btn2.click(fn=pick_video_2, inputs=[session_state], outputs=[choice_display, session_state])
        return demo

if __name__ == "__main__":
    create_demo().launch(share=True)