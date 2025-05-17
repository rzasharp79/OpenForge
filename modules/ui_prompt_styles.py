import json
import os

import gradio as gr

from modules import shared, ui_common, ui_components, styles, sd_samplers, sd_schedulers, util
from modules.paths_internal import script_path

slot_machine_symbol = "\U0001f3b0"  # 🎰
config_open_symbol = "\U0001f5c3"  # 🗃

config_path = os.path.join(script_path, "randomize_sampler_config.json")
randomize_config = {}

styles_edit_symbol = '\U0001f58c\uFE0F'  # 🖌️
styles_materialize_symbol = '\U0001f4cb'  # 📋
styles_copy_symbol = '\U0001f4dd'  # 📝


def select_style(name):
    style = shared.prompt_styles.styles.get(name)
    existing = style is not None
    empty = not name

    prompt = style.prompt if style else gr.update()
    negative_prompt = style.negative_prompt if style else gr.update()

    return prompt, negative_prompt, gr.update(visible=existing), gr.update(visible=not empty)


def save_style(name, prompt, negative_prompt):
    if not name:
        return gr.update(visible=False)

    existing_style = shared.prompt_styles.styles.get(name)
    path = existing_style.path if existing_style is not None else None

    style = styles.PromptStyle(name, prompt, negative_prompt, path)
    shared.prompt_styles.styles[style.name] = style
    shared.prompt_styles.save_styles()

    return gr.update(visible=True)


def delete_style(name):
    if name == "":
        return

    shared.prompt_styles.styles.pop(name, None)
    shared.prompt_styles.save_styles()

    return '', '', ''


def materialize_styles(prompt, negative_prompt, styles):
    prompt = shared.prompt_styles.apply_styles_to_prompt(prompt, styles)
    negative_prompt = shared.prompt_styles.apply_negative_styles_to_prompt(negative_prompt, styles)

    return [gr.Textbox.update(value=prompt), gr.Textbox.update(value=negative_prompt), gr.Dropdown.update(value=[])]


def refresh_styles():
    return gr.update(choices=list(shared.prompt_styles.styles)), gr.update(choices=list(shared.prompt_styles.styles))


def load_randomize_config():
    global randomize_config
    default = {
        "min_cfg": 1,
        "max_cfg": 10,
        "min_distilled_cfg": 0,
        "max_distilled_cfg": 10,
        "min_steps": 10,
        "max_steps": 50,
        "samplers": [],
        "schedulers": [],
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                randomize_config = json.load(f)
        except Exception as exc:
            print(f"Failed to read {config_path}: {exc}")
            randomize_config = {}
    else:
        randomize_config = {}

    for key, val in default.items():
        randomize_config.setdefault(key, val)

    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(randomize_config, f, indent=2)


def refresh_randomize_config():
    load_randomize_config()


def open_randomize_config_file():
    util.open_file_in_editor(config_path)


load_randomize_config()


def randomize_sampler():
    import random

    load_randomize_config()

    samplers_pool = randomize_config.get("samplers") or sd_samplers.visible_sampler_names()
    schedulers_pool = randomize_config.get("schedulers") or [x.label for x in sd_schedulers.schedulers]

    samplers_pool = [s for s in samplers_pool if s in sd_samplers.visible_sampler_names()]
    schedulers_pool = [s for s in schedulers_pool if s in [x.label for x in sd_schedulers.schedulers]]

    sampler = random.choice(samplers_pool)
    scheduler = random.choice(schedulers_pool)
    steps = random.randint(randomize_config.get("min_steps", 10), randomize_config.get("max_steps", 50))
    cfg = round(random.uniform(randomize_config.get("min_cfg", 1), randomize_config.get("max_cfg", 10)), 1)
    dcfg = round(random.uniform(randomize_config.get("min_distilled_cfg", 0), randomize_config.get("max_distilled_cfg", 10)), 1)

    return sampler, scheduler, steps, cfg, dcfg


class UiPromptStyles:
    def __init__(self, tabname, main_ui_prompt, main_ui_negative_prompt):
        self.tabname = tabname
        self.main_ui_prompt = main_ui_prompt
        self.main_ui_negative_prompt = main_ui_negative_prompt

        with gr.Row(elem_id=f"{tabname}_styles_row"):
            self.dropdown = gr.Dropdown(label="Styles", show_label=False, elem_id=f"{tabname}_styles", choices=list(shared.prompt_styles.styles), value=[], multiselect=True, tooltip="Styles")
            edit_button = ui_components.ToolButton(value=styles_edit_symbol, elem_id=f"{tabname}_styles_edit_button", tooltip="Edit styles")
            self.randomize = ui_components.ToolButton(value=slot_machine_symbol, elem_id=f"{tabname}_randomize_sampling", tooltip="Randomize sampler settings")
            self.edit_randomize = ui_components.ToolButton(value=config_open_symbol, elem_id=f"{tabname}_randomize_config_open", tooltip="Open configuration file for randomize sampler")
            self.refresh_randomize = ui_components.ToolButton(value=ui_common.refresh_symbol, elem_id=f"{tabname}_randomize_config_refresh", tooltip="Refresh randomize sampler configuration")

        with gr.Box(elem_id=f"{tabname}_styles_dialog", elem_classes="popup-dialog") as styles_dialog:
            with gr.Row():
                self.selection = gr.Dropdown(label="Styles", elem_id=f"{tabname}_styles_edit_select", choices=list(shared.prompt_styles.styles), value=[], allow_custom_value=True, info="Styles allow you to add custom text to prompt. Use the {prompt} token in style text, and it will be replaced with user's prompt when applying style. Otherwise, style's text will be added to the end of the prompt.")
                ui_common.create_refresh_button([self.dropdown, self.selection], shared.prompt_styles.reload, lambda: {"choices": list(shared.prompt_styles.styles)}, f"refresh_{tabname}_styles")
                self.materialize = ui_components.ToolButton(value=styles_materialize_symbol, elem_id=f"{tabname}_style_apply_dialog", tooltip="Apply all selected styles from the style selection dropdown in main UI to the prompt. Strips comments, if enabled.")
                self.copy = ui_components.ToolButton(value=styles_copy_symbol, elem_id=f"{tabname}_style_copy", tooltip="Copy main UI prompt to style.")

            with gr.Row():
                self.prompt = gr.Textbox(label="Prompt", show_label=True, elem_id=f"{tabname}_edit_style_prompt", lines=3, elem_classes=["prompt"])

            with gr.Row():
                self.neg_prompt = gr.Textbox(label="Negative prompt", show_label=True, elem_id=f"{tabname}_edit_style_neg_prompt", lines=3, elem_classes=["prompt"])

            with gr.Row():
                self.save = gr.Button('Save', variant='primary', elem_id=f'{tabname}_edit_style_save', visible=False)
                self.delete = gr.Button('Delete', variant='primary', elem_id=f'{tabname}_edit_style_delete', visible=False)
                self.close = gr.Button('Close', variant='secondary', elem_id=f'{tabname}_edit_style_close')

        self.selection.change(
            fn=select_style,
            inputs=[self.selection],
            outputs=[self.prompt, self.neg_prompt, self.delete, self.save],
            show_progress=False,
        )

        self.save.click(
            fn=save_style,
            inputs=[self.selection, self.prompt, self.neg_prompt],
            outputs=[self.delete],
            show_progress=False,
        ).then(refresh_styles, outputs=[self.dropdown, self.selection], show_progress=False)

        self.delete.click(
            fn=delete_style,
            _js='function(name){ if(name == "") return ""; return confirm("Delete style " + name + "?") ? name : ""; }',
            inputs=[self.selection],
            outputs=[self.selection, self.prompt, self.neg_prompt],
            show_progress=False,
        ).then(refresh_styles, outputs=[self.dropdown, self.selection], show_progress=False)

        self.setup_apply_button(self.materialize)

        self.copy.click(
            fn=lambda p, n: (p, n),
            inputs=[main_ui_prompt, main_ui_negative_prompt],
            outputs=[self.prompt, self.neg_prompt],
            show_progress=False,
        )

        self.setup_randomize_config_buttons(self.edit_randomize, self.refresh_randomize)

        ui_common.setup_dialog(button_show=edit_button, dialog=styles_dialog, button_close=self.close)

    def setup_randomize_button(self, button, sampler_name, scheduler, steps, cfg, distilled_cfg):
        button.click(
            fn=randomize_sampler,
            inputs=[],
            outputs=[sampler_name, scheduler, steps, cfg, distilled_cfg],
            show_progress=False,
        )

    def setup_randomize_config_buttons(self, open_button, refresh_button):
        open_button.click(fn=open_randomize_config_file, inputs=[], outputs=[], show_progress=False)
        refresh_button.click(fn=refresh_randomize_config, inputs=[], outputs=[], show_progress=False)

    def setup_apply_button(self, button):
        button.click(
            fn=materialize_styles,
            inputs=[self.main_ui_prompt, self.main_ui_negative_prompt, self.dropdown],
            outputs=[self.main_ui_prompt, self.main_ui_negative_prompt, self.dropdown],
            show_progress=False,
        ).then(fn=None, _js="function(){update_"+self.tabname+"_tokens(); closePopup();}", show_progress=False)
