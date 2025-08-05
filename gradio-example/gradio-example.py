import gradio as gr
import json
import os
import uuid

def load_counts(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            counts = json.load(f)
        counts.setdefault("video1_ratings", [])
        counts.setdefault("video2_ratings", [])
        counts.setdefault("comments", [])
        if isinstance(counts.get("comments"), str):
            counts["comments"] = [counts["comments"]]
    else:
        counts = {
            "video1_count": 0,
            "video2_count": 0,
            "video1_ratings": [],
            "video2_ratings": [],
            "comments": []
        }
    return counts

def save_counts(counts, file_path):
    with open(file_path, "w") as f:
        json.dump(counts, f)

def create_demo(video1_path="robot_Example1.mp4", video2_path="robot_Example2.mp4", 
                curr_dir="video-data/vid-pair1/", result_dir="eval-results/"):
    video1_path = f"{curr_dir + video1_path}"
    video2_path = f"{curr_dir + video2_path}"
    

    def pick_video_1(state):
        if state["session_file"] is None:
            state["session_file"] = f"counts_{uuid.uuid4().hex}.json"
        result_path = f"{result_dir + state['session_file']}"
        counts = load_counts(result_path)
        prev = state["prev_choice"]
        if prev == 1:
            return "video 1 chosen", state
        if prev == 2:
            counts["video2_count"] -= 1
        counts["video1_count"] += 1
        save_counts(counts, result_path)
        state["prev_choice"] = 1
        return "video 1 chosen", state

    def pick_video_2(state):
        if state["session_file"] is None:
            state["session_file"] = f"counts_{uuid.uuid4().hex}.json"
        result_path = f"{result_dir + state['session_file']}"
        counts = load_counts(result_path)
        prev = state["prev_choice"]
        if prev == 2:
            return "video 2 chosen", state
        if prev == 1:
            counts["video1_count"] -= 1
        counts["video2_count"] += 1
        save_counts(counts, result_path)
        state["prev_choice"] = 2
        return "video 2 chosen", state
    
    def submit_rating(state, rating):
        if state["session_file"] is None:
            return "Please choose a video first", state
        result_path = f"{result_dir + state['session_file']}"
        counts = load_counts(result_path)
        choice = state["prev_choice"]
        if choice not in (1, 2):
            return "Please choose a video first", state
        key = f"video{choice}_ratings"
        counts.setdefault(key, []).append(int(rating))
        save_counts(counts, result_path)
        return state
    
    def submit_comment(state, new_comment):
        if state["session_file"] is None:
            return "Please choose a video first", state
        result_path = f"{result_dir + state['session_file']}"
        counts = load_counts(result_path)
        comments = counts.get("comments", [])
        if not isinstance(comments, list):
            comments = [comments]
            counts["comments"] = comments
        comments.append(new_comment)
        save_counts(counts, result_path)        
        return state


    with gr.Blocks() as demo:
        session_state = gr.State({"session_file": None, "prev_choice": 0})
        gr.Markdown("## Select a Video and Rate It")
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
        rating_slider = gr.Slider(label="Rate the currently selected video (1–10)", minimum=1, maximum=10, step=1, value=5)
        submit_rating_btn = gr.Button("Submit Rating")
        comment_box = gr.Textbox(label="Comment (type then submit)", placeholder="Type your comment here...")
        submit_comment_btn = gr.Button("Save Comment")

        btn1.click(fn=pick_video_1, inputs=[session_state], outputs=[choice_display, session_state])
        btn2.click(fn=pick_video_2, inputs=[session_state], outputs=[choice_display, session_state])
        submit_rating_btn.click(
            fn=submit_rating,
            inputs=[session_state, rating_slider],
            outputs=[session_state],
        )
        submit_comment_btn.click(fn=submit_comment, inputs=[session_state, comment_box], outputs=[session_state])
        return demo

if __name__ == "__main__":
    create_demo().launch(share=True)