# app.py
import gradio as gr
import json, os, uuid, re
from tasks_ui import detect_task_from_dirs, build_task_ui  # <--- task UI module

VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi")

# ---------- helpers ----------

def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def load_counts(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            counts = json.load(f)
    else:
        counts = {}
    counts.setdefault("per_pair", {})  # {pair_id: {...}}
    return counts

def save_counts(counts, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(counts, f, indent=2, sort_keys=True)
        f.write("\n")

def get_pair_counts(counts, pair_id):
    return counts["per_pair"].setdefault(pair_id, {
        "video1_count": 0,
        "video2_count": 0,
        "comments": [],
        "task_q": [],         # task-specific submissions
        "general_q": []       # general 1–10 scale submissions
    })

def find_pairs_two_dirs(dir1, dir2):
    v1s = sorted([os.path.join(dir1, f) for f in os.listdir(dir1)
                  if f.lower().endswith(VIDEO_EXTS)], key=natural_key)
    v2s = sorted([os.path.join(dir2, f) for f in os.listdir(dir2)
                  if f.lower().endswith(VIDEO_EXTS)], key=natural_key)
    n = min(len(v1s), len(v2s))
    if n == 0:
        raise RuntimeError("No videos found. Check folder paths/extensions.")
    pairs = []
    for i in range(n):
        b1, b2 = os.path.basename(v1s[i]), os.path.basename(v2s[i])
        pair_id = f"{i:03d}:{b1}|{b2}"  # stable key
        title = f"{i+1}: {b1}  ↔  {b2}"
        pairs.append({"id": pair_id, "title": title, "v1": v1s[i], "v2": v2s[i]})
    return pairs

# ---------- app ----------

def create_demo(dir1="video-data/folder1", dir2="video-data/folder2", result_dir="eval-results/"):
    pairs = find_pairs_two_dirs(dir1, dir2)
    task = detect_task_from_dirs(dir1, dir2)

    def load_session(state):
        if state["session_file"] is None:
            state["session_file"] = f"counts_{uuid.uuid4().hex}.json"
        result_path = os.path.join(result_dir, state["session_file"])
        return load_counts(result_path), result_path

    def current_pair(state):
        return state["pairs"][state["pair_idx"]]

    def _pick(choice, state):
        counts, result_path = load_session(state)
        pair = current_pair(state)
        pair_id = pair["id"]
        prev = state["choices"].get(pair_id, 0)
        per = get_pair_counts(counts, pair_id)

        if prev == choice:
            return f"video {choice} chosen", state

        if prev == 1:
            per["video1_count"] -= 1
        elif prev == 2:
            per["video2_count"] -= 1

        if choice == 1:
            per["video1_count"] += 1
        else:
            per["video2_count"] += 1

        state["choices"][pair_id] = choice
        save_counts(counts, result_path)
        return f"video {choice} chosen", state

    def pick_video_1(state): return _pick(1, state)
    def pick_video_2(state): return _pick(2, state)

    def submit_comment(state, new_comment):
        counts, result_path = load_session(state)
        per = get_pair_counts(counts, current_pair(state)["id"])

        text = (new_comment or "").strip()
        if not text:
            return "Nothing to save (comment was empty).", state

        per["comments"] = [text]
        save_counts(counts, result_path)
        return "Saved comment", state

    def submit_general(state, smooth, coord, safety):
        counts, result_path = load_session(state)
        per = get_pair_counts(counts, current_pair(state)["id"])
        entry = {
            "smoothness_1to10": int(smooth),
            "coordination_1to10": int(coord),
            "safety_collisions_1to10": int(safety),
        }
        per["general_q"] = [entry]
        save_counts(counts, result_path)
        return "Saved general answers", state

    def goto_pair(state, idx):
        n = len(state["pairs"])
        state["pair_idx"] = max(0, min(n - 1, idx))
        pair = current_pair(state)
        pair_id = pair["id"]

        prev_choice = state["choices"].get(pair_id, 0)
        choice_text = ("video 1 chosen" if prev_choice == 1
                       else "video 2 chosen" if prev_choice == 2
                       else "")

        header = f"### Pair {state['pair_idx'] + 1}/{n}: {pair['title']}"
        return (gr.update(value=pair["v1"]),
                gr.update(value=pair["v2"]),
                gr.update(value=header),
                gr.update(value=choice_text),
                state)

    def next_pair(state): return goto_pair(state, state["pair_idx"] + 1)
    def prev_pair(state): return goto_pair(state, state["pair_idx"] - 1)

    def on_submit_task(task_name: str, state: dict, answers: dict):
        counts, result_path = load_session(state)
        per = get_pair_counts(counts, current_pair(state)["id"])
        entry = {"task": task_name, **answers}

        lst = per.get("task_q", [])
        for i, e in enumerate(lst):
            if e.get("task") == task_name:
                lst[i] = entry
                break
        else:
            lst.append(entry)

        per["task_q"] = lst
        save_counts(counts, result_path)
        return "Saved task answers", state

    with gr.Blocks() as demo:
        session_state = gr.State({
            "session_file": None,
            "pairs": pairs,
            "pair_idx": 0,
            "choices": {},   # {pair_id: 1|2}
            "task": task
        })

        gr.Markdown(f"**Detected task:** `{task}`")

        with gr.Row():
            with gr.Column(scale=0, min_width=120):
                btn_prev = gr.Button("◀ Prev Pair")
            with gr.Column(scale=0, min_width=120):
                btn_next = gr.Button("Next Pair ▶")

        first = pairs[0]
        title = gr.Markdown(f"### Pair 1/{len(pairs)}: {first['title']}")
        gr.Markdown("Select a Video and Rate It")

        with gr.Row():
            video1 = gr.Video(value=first["v1"], label="Video 1", interactive=False)
            video2 = gr.Video(value=first["v2"], label="Video 2", interactive=False)

        with gr.Row():
            btn1 = gr.Button("Choose Video 1")
            btn2 = gr.Button("Choose Video 2")

        choice_display = gr.Textbox(label="Your choice", interactive=False)

        comment = gr.Textbox(label="Comment (type then submit)",
                             placeholder="Type your comment here...")
        submit_comment_btn = gr.Button("Save Comment")
        status = gr.Markdown()

        # choices / comments
        btn1.click(pick_video_1, inputs=[session_state], outputs=[choice_display, session_state])
        btn2.click(pick_video_2, inputs=[session_state], outputs=[choice_display, session_state])
        submit_comment_btn.click(submit_comment, inputs=[session_state, comment],
                                 outputs=[status, session_state])

        # navigation (wires to the top buttons)
        btn_next.click(next_pair, inputs=[session_state],
                       outputs=[video1, video2, title, choice_display, session_state])
        btn_prev.click(prev_pair, inputs=[session_state],
                       outputs=[video1, video2, title, choice_display, session_state])

        # ----- General evaluation (1–10 scale) — always visible
        gr.Markdown("### General evaluation (1–10 scale)")
        gr.Markdown(
            "**Scale guidance:** 1 → significant unstable/jerky motions (worst), "
            "10 → completely smooth movements (best). Applies to smoothness, coordination, and safety."
        )
        gen_smooth = gr.Slider(
            1, 10, step=1, value=5,
            label="How smooth were the robot’s movements? (1 = significant unstable/jerky motions, 10 = completely smooth)"
        )
        gen_coord = gr.Slider(
            1, 10, step=1, value=5,
            label="Was there coordination between the two arms? (1 = dominated by one arm / poor coordination, 10 = excellent bimanual coordination)"
        )
        gen_safety = gr.Slider(
            1, 10, step=1, value=5,
            label="Did the robot avoid collisions and handle objects safely? (1 = frequent/severe collisions or unsafe handling, 10 = no collisions / fully safe)"
        )
        gen_submit = gr.Button("Save General Answers")
        gen_submit.click(
            submit_general,
            inputs=[session_state, gen_smooth, gen_coord, gen_safety],
            outputs=[status, session_state],
        )

        # ---- task-specific UI (from module)
        gr.Markdown("### Task-specific questions")
        build_task_ui(task, session_state, status, on_submit_task)

        return demo

if __name__ == "__main__":
    # create_demo(
    #     "video-data/bc_state/rotate_gate_valve/eval_videos",
    #     "video-data/diffusion_state/rotate_gate_valve/eval_videos",
    #     "eval-results/"
    # ).launch(share=True)

    create_demo(
        "video-data/bc_state/rotate_lever_easy/eval_videos",
        "video-data/diffusion_pixel/rotate_lever_easy/eval_videos",
        "eval-results/"
    ).launch(share=True)