# tasks_ui.py
import gradio as gr
import re

# Add new tasks here and create a matching UI group below.
KNOWN_TASKS = {"rotate_gate_valve", "rotate_lever_easy"}

def detect_task_from_dirs(*dirs) -> str:
    """Return a task slug from folder names if found, else 'generic'."""
    parts = []
    for d in dirs:
        parts += re.split(r"[\\/]", str(d).lower())
    # exact token match first
    for p in parts:
        if p in KNOWN_TASKS:
            return p
    # substring fallback
    for t in KNOWN_TASKS:
        if any(t in p for p in parts):
            return t
    return "generic"


def build_task_ui(task: str, session_state: gr.State, status_out: gr.Markdown, on_submit):
    """
    Build task-specific panels and wire submit buttons.

    Parameters
    ----------
    task : str
        Detected task slug (e.g., 'rotate_gate_valve', 'rotate_lever_easy', 'generic').
    session_state : gr.State
        Your app's state object (dict) so handlers can read/modify it.
    status_out : gr.Markdown
        A status component to display "Saved ..." messages.
    on_submit : callable
        Signature: on_submit(task: str, state: dict, answers: dict) -> (str, dict)
        Should return (status_message, state).
    """
    # rotate_gate_valve
    with gr.Group(visible=(task == "rotate_gate_valve")):
        rv_all = gr.Radio(
            ["No", "Yes"], value="No",
            label="Was the valve turned all the way? (Should be x degrees turned)"
        )
        rv_time = gr.Number(
            label="Time to complete (s)", value=None, precision=2,
            visible=False  # only when 'turned all the way' == Yes
        )

        rv_both = gr.Radio(
            ["No", "Yes"], value="No",
            label="Did both grippers grip the valve simultaneously before turning?"
        )
        rv_slip = gr.Radio(
            ["No", "Yes"], value="No",
            label="Did the gripper slip off the valve at any point?",
            visible=False  # only when rv_both == Yes
        )
        rv_any_grip = gr.Radio(
            ["No", "Yes"], value="No",
            label="Was the valve gripped at any point?",
            visible=True   # only when rv_both == No
        )

        rv_submit = gr.Button("Save Task Answers")

        # Toggle time input when all_the_way == Yes
        def _toggle_time(all_the_way):
            return gr.update(visible=(all_the_way == "Yes"), value=None)

        rv_all.change(_toggle_time, inputs=[rv_all], outputs=[rv_time])

        # Toggle slip vs any_grip depending on both-grip answer
        def _toggle_grip(both):
            show_slip = (both == "Yes")
            return (
                gr.update(visible=show_slip, value="No"),
                gr.update(visible=not show_slip, value="No"),
            )

        rv_both.change(_toggle_grip, inputs=[rv_both], outputs=[rv_slip, rv_any_grip])

        def _rv_handler(state, all_the_way, time_s, both_simul, slip, any_grip):
            answers = {
                "turned_all_the_way": (all_the_way == "Yes"),
                "time_s": (
                    float(time_s) if (all_the_way == "Yes" and time_s not in (None, ""))
                    else None
                ),
                "both_grip_simultaneous_before_turn": (both_simul == "Yes"),
                "gripper_slip_any_point": (slip == "Yes") if (both_simul == "Yes") else None,
                "gripped_at_any_point": (any_grip == "Yes") if (both_simul == "No") else None,
            }
            return on_submit("rotate_gate_valve", state, answers)

        rv_submit.click(
            _rv_handler,
            inputs=[session_state, rv_all, rv_time, rv_both, rv_slip, rv_any_grip],
            outputs=[status_out, session_state],
        )

    # rotate_lever_easy
    with gr.Group(visible=(task == "rotate_lever_easy")):
        rl_all = gr.Radio(
            ["No", "Yes"], value="No",
            label="Was the lever moved fully to the target position?"
        )
        rl_time = gr.Number(
            label="Time to complete (s)", value=None, precision=2,
            visible=False  # only when 'Yes'
        )

        rl_both = gr.Radio(
            ["No", "Yes"], value="No",
            label="Did both grippers grip the lever simultaneously before turning?"
        )
        rl_slip = gr.Radio(
            ["No", "Yes"], value="No",
            label="Did the gripper slip off the lever at any point?",
            visible=False  # only when rl_both == Yes
        )
        rl_any_grip = gr.Radio(
            ["No", "Yes"], value="No",
            label="Was the lever gripped at any point?",
            visible=True   # only when rl_both == No
        )

        rl_submit = gr.Button("Save Task Answers")

        def _toggle_time_lever(all_the_way):
            return gr.update(visible=(all_the_way == "Yes"), value=None)

        rl_all.change(_toggle_time_lever, inputs=[rl_all], outputs=[rl_time])

        def _toggle_grip_lever(both):
            show_slip = (both == "Yes")
            return (
                gr.update(visible=show_slip, value="No"),
                gr.update(visible=not show_slip, value="No"),
            )

        rl_both.change(_toggle_grip_lever, inputs=[rl_both], outputs=[rl_slip, rl_any_grip])

        def _rl_handler(state, all_the_way, time_s, both_simul, slip, any_grip):
            answers = {
                "moved_to_target": (all_the_way == "Yes"),
                "time_s": (
                    float(time_s) if (all_the_way == "Yes" and time_s not in (None, ""))
                    else None
                ),
                "both_grip_simultaneous_before_turn": (both_simul == "Yes"),
                "gripper_slip_any_point": (slip == "Yes") if (both_simul == "Yes") else None,
                "gripped_at_any_point": (any_grip == "Yes") if (both_simul == "No") else None,
            }
            return on_submit("rotate_lever_easy", state, answers)

        rl_submit.click(
            _rl_handler,
            inputs=[session_state, rl_all, rl_time, rl_both, rl_slip, rl_any_grip],
            outputs=[status_out, session_state],
        )

    # generic questions
    with gr.Group(visible=(task == "generic")):
        gen_success = gr.Radio(["No", "Yes"], value="Yes", label="Task successful overall?")
        gen_time = gr.Number(label="Time to complete (s)", value=None, precision=2)
        gen_submit = gr.Button("Save Task Answers")

        def _gen_handler(state, success, time_s):
            answers = {
                "success": (success == "Yes"),
                "time_s": float(time_s) if time_s not in (None, "") else None,
            }
            return on_submit("generic", state, answers)

        gen_submit.click(
            _gen_handler,
            inputs=[session_state, gen_success, gen_time],
            outputs=[status_out, session_state],
        )