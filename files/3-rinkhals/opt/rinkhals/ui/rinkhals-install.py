import time

start = time.time()
import os
import logging
print(f"imports: {time.time() - start:.2f}s")

start = time.time()
import lvgl as lv
import lvgl_rinkhals as lvr
print(f"lv, lvr: {time.time() - start:.2f}s")

start = time.time()
from common import *
print(f"common: {time.time() - start:.2f}s")


DEBUG_LOGGING = os.getenv('DEBUG_LOGGING')
DEBUG_LOGGING = not not DEBUG_LOGGING

DEBUG_RENDERING = os.getenv('DEBUG_RENDERING')
DEBUG_RENDERING = not not DEBUG_RENDERING
#DEBUG_RENDERING = True

if DEBUG_LOGGING:
    logging.getLogger().setLevel(logging.DEBUG)

lvr.set_debug_rendering(DEBUG_RENDERING)

if USING_SIMULATOR:
    PrinterInfo.simulate(
        model_code='K3',
        model='Anycubic Kobra',
        #rinkhals_version='20250401_01_test',
        rinkhals_version='20250409_01',
        system_version='2.4.0',
    )


TOOLS_PATH = os.path.join(SCRIPT_PATH, 'tools')

class Tool:
    def __init__(self, name, icon, command, description, action=None, action_color=None):
        self.name = name
        self.icon = icon
        self.command = command
        self.description = description
        self.action = action
        self.action_color = action_color

tools = [
    tool_debug_bundle := Tool('Generate a Debug Bundle', '', 'debug-bundle.sh', 'This tool will generate a debug bundle on the attached USB drive.\nIt will take 10 to 15 seconds. Do you want to proceed?', 'Yes'),
    tool_reset_config := Tool('Reset Rinkhals configuration', '', 'config-reset.sh', 'This tool will reset all Rinkhals configuration. Your printer will be like the first time you installed Rinkhals.\nYour printer will then reboot. Do you want to proceed?', 'Yes', lvr.COLOR_DANGER),
    tool_backup_partitions := Tool('Backup partitions', '', 'backup-partitions.sh', 'This tool will backup your printer /userdata and /useremain partition on the attached USB drive.\nIt will take up to a minute. Do you want to proceed?', 'Yes'),
    tool_clean_rinkhals := Tool('Clean old Rinkhals', '', 'clean-rinkhals.sh', 'This tool will remove old installed Rinkhals versions. 2 versions and the current one will be kept. Do you want to proceed?', 'Yes'),
    tool_uninstall_rinkhals := Tool('Uninstall Rinkhals', '', 'rinkhals-uninstall.sh', 'This tool will completely uninstall Rinkhals from your printer. Do you want to proceed?', 'Yes', lvr.COLOR_DANGER),
    #tool_factory_reset := Tool('Factory reset', '', 'factory-reset.sh', 'The tool will factory reset your printer', 'Yes', lvr.COLOR_DANGER),
]


class RinkhalsInstallApp(BaseApp):
    diagnostics_cache: list[Diagnostic] = None

    def layout(self):
        self.screen_welcome = lvr.screen(tag='screen_welcome')
        if self.screen_welcome:
            self.screen_welcome.set_flex_flow(lv.FLEX_FLOW.COLUMN)
            self.screen_welcome.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
            self.screen_welcome.set_style_pad_row(lv.dpx(25), lv.STATE.DEFAULT)

            image_rinkhals = lvr.image(self.screen_welcome)
            image_rinkhals.set_src(ASSETS_PATH + '/icon.png')
            image_rinkhals.scale_to(lv.dpx(100))

            label_title = lvr.title(self.screen_welcome)
            label_title.set_text('Rinkhals Installer')

            def show_main():
                self.show_screen(self.screen_main)

            button_start = lvr.button(self.screen_welcome)
            button_start.set_width(lv.dpx(200))
            button_start.set_style_margin_top(lv.dpx(20), lv.STATE.DEFAULT)
            button_start.add_event_cb(lambda e: show_main(), lv.EVENT_CODE.CLICKED, None)
            button_start_label = lvr.label(button_start)
            button_start_label.set_text('Continue')
            button_start_label.center()
                
            button_exit = lvr.button_icon(self.screen_welcome)
            button_exit.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
            button_exit.align(lv.ALIGN.TOP_LEFT, -lvr.get_global_margin(), -lvr.get_global_margin())
            button_exit.set_text('')
            button_exit.add_event_cb(lambda e: self.quit(), lv.EVENT_CODE.CLICKED, None)

            def anim_1_cb(o, value, image_rinkhals=image_rinkhals, label_title=label_title):
                image_rinkhals.set_style_opa(value * 255 // 100, lv.STATE.DEFAULT)
                image_rinkhals.set_style_margin_top(-lv.dpx(int((100 - value) * 1.6)), lv.STATE.DEFAULT)
                label_title.set_style_opa(value * 255 // 100, lv.STATE.DEFAULT)

            def anim_2_cb(o, value, button_start=button_start):
                button_start.set_style_opa(value * 255 // 100, lv.STATE.DEFAULT)

            initial_delay = 500
            anim_1_duration = 750

            self.screen_welcome.anim_1 = lv.anim()
            self.screen_welcome.anim_1.set_exec_cb(anim_1_cb)
            self.screen_welcome.anim_1.set_delay(initial_delay)
            self.screen_welcome.anim_1.set_duration(anim_1_duration)
            self.screen_welcome.anim_1.set_values(0, 100)
            self.screen_welcome.anim_1.set_path_cb(lv.anim_path_ease_out)

            anim_2_duration = 500
            
            self.screen_welcome.anim_2 = lv.anim()
            self.screen_welcome.anim_2.set_exec_cb(anim_2_cb)
            self.screen_welcome.anim_2.set_delay(initial_delay + anim_1_duration - 250)
            self.screen_welcome.anim_2.set_duration(anim_2_duration)
            self.screen_welcome.anim_2.set_values(0, 100)
            self.screen_welcome.anim_2.set_path_cb(lv.anim_path_ease_out)
            self.screen_welcome.anim_2.set_completed_cb(lambda e: run_async(self.layout_async))

        lv.screen_load(self.screen_welcome)

        self.screen_welcome.anim_1.start()
        self.screen_welcome.anim_2.start()

        run_async(self.preload)
    def layout_async(self):
        with lvr.lock():
            super().layout()
            lv.screen_load(self.screen_welcome)

        with lvr.lock():
            if self.screen_logo:
                self.screen_logo.set_flex_flow(lv.FLEX_FLOW.COLUMN)
                self.screen_logo.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                self.screen_logo.set_style_pad_row(-lv.dpx(3), lv.STATE.DEFAULT)

                rinkhals_icon = lvr.image(self.screen_logo)
                rinkhals_icon.set_src(ASSETS_PATH + '/icon.png')
                rinkhals_icon.scale_to(lv.dpx(70))

                label_rinkhals = lvr.title(self.screen_logo)
                label_rinkhals.set_text('Rinkhals Installer')
                label_rinkhals.set_style_pad_top(lv.dpx(20), lv.STATE.DEFAULT)
                label_rinkhals.set_style_pad_bottom(lv.dpx(10), lv.STATE.DEFAULT)
                
                self.screen_logo.panel_tags = lvr.panel(self.screen_logo)
                self.screen_logo.panel_tags.set_width(lv.pct(100))
                self.screen_logo.panel_tags.set_align(lv.ALIGN.BOTTOM_MID)
                self.screen_logo.panel_tags.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)
                self.screen_logo.panel_tags.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_logo.panel_tags.set_flex_flow(lv.FLEX_FLOW.COLUMN)
                self.screen_logo.panel_tags.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                
                button_exit = lvr.button_icon(self.screen_logo)
                button_exit.add_flag(lv.OBJ_FLAG.IGNORE_LAYOUT)
                button_exit.align(lv.ALIGN.TOP_LEFT, -lvr.get_global_margin(), -lvr.get_global_margin())
                button_exit.set_text('')
                button_exit.add_event_cb(lambda e: self.quit(), lv.EVENT_CODE.CLICKED, None)

        with lvr.lock():
            if self.screen_main:
                self.screen_main.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_main.set_flex_flow(lv.FLEX_FLOW.COLUMN)
                self.screen_main.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

                panel_tools = lvr.panel(self.screen_main, lv.FLEX_FLOW.ROW_WRAP)
                panel_tools.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)
                panel_tools.set_size(lv.pct(100), lv.pct(100))

                button_count = 2
                panel_width = self.screen_info.width / (2 if self.screen_info.width > self.screen_info.height else 1)
                button_width = (panel_width - lvr.get_global_margin() * (button_count + 1)) / button_count
                button_width = int(button_width)

                button_install = lvr.button(panel_tools)
                button_install.set_size(button_width, lvr.get_large_button_height())
                button_install.set_text('Install & Updates')
                button_install.set_icon('')
                button_install.add_event_cb(lambda e: self.show_screen(self.screen_ota), lv.EVENT_CODE.CLICKED, None)

                button_tools = lvr.button(panel_tools)
                button_tools.set_size(button_width, lvr.get_large_button_height())
                button_tools.set_text('Tools')
                button_tools.set_icon('')
                button_tools.add_event_cb(lambda e: self.show_screen(self.screen_tools), lv.EVENT_CODE.CLICKED, None)

                button_diagnostics = lvr.button(panel_tools)
                button_diagnostics.set_size(button_width, lvr.get_large_button_height())
                button_diagnostics.set_text('Diagnostics')
                button_diagnostics.set_icon('')
                button_diagnostics.add_event_cb(lambda e: self.show_screen(self.screen_diagnostics), lv.EVENT_CODE.CLICKED, None)

                button_reboot = lvr.button(panel_tools)
                button_reboot.set_size(button_width, lvr.get_large_button_height())
                button_reboot.set_text('Reboot')
                button_reboot.set_icon('')
                button_reboot.add_event_cb(lambda e: self.show_text_dialog('Are you sure\nyou want to reboot?', 'Yes', callback=lambda: system('sync && reboot')), lv.EVENT_CODE.CLICKED, None)

        with lvr.lock():
            self.layout_ota()
        with lvr.lock():
            self.layout_ota_rinkhals()
        with lvr.lock():
            self.layout_ota_firmware()
            
        with lvr.lock():
            self.screen_tools = lvr.panel(self.root_screen, tag='screen_tools')
            if self.screen_tools:
                self.screen_tools.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_tools.set_size(lv.pct(100), lv.pct(100))
                self.screen_tools.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_tools.set_style_pad_top(lvr.get_title_bar_height(), lv.STATE.DEFAULT)

                title_bar = lvr.title_bar(self.screen_tools)
                title_bar.set_y(-lvr.get_title_bar_height())
                
                title = lvr.title(title_bar)
                title.set_text('Tools')
                title.center()

                icon_back = lvr.button_icon(title_bar)
                icon_back.set_align(lv.ALIGN.LEFT_MID)
                icon_back.set_text('')
                icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)

                panel_tools = lvr.panel(self.screen_tools, lv.FLEX_FLOW.ROW_WRAP)
                panel_tools.set_style_bg_opa(lv.OPA.TRANSP, lv.STATE.DEFAULT)
                panel_tools.set_size(lv.pct(100), lv.pct(100))

                button_count = 2
                panel_width = self.screen_info.width / (2 if self.screen_info.width > self.screen_info.height else 1)
                button_width = (panel_width - lvr.get_global_margin() * (button_count + 1)) / button_count
                button_width = int(button_width)

                for t in tools:
                    button_debug_bundle = lvr.button(panel_tools)
                    button_debug_bundle.set_size(button_width, lvr.get_large_button_height())
                    button_debug_bundle.set_text(t.name)
                    button_debug_bundle.set_icon(t.icon)
                    button_debug_bundle.add_event_cb(lambda e, t=t: self.show_tool_modal(t), lv.EVENT_CODE.CLICKED, None)

        with lvr.lock():
            self.screen_diagnostics = lvr.panel(self.root_screen, flex_flow=lv.FLEX_FLOW.COLUMN, tag='screen_diagnostics')
            if self.screen_diagnostics:
                self.screen_diagnostics.add_flag(lv.OBJ_FLAG.HIDDEN)
                self.screen_diagnostics.set_size(lv.pct(100), lv.pct(100))
                self.screen_diagnostics.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_diagnostics.set_style_pad_row(0, lv.STATE.DEFAULT)

                title_bar = lvr.title_bar(self.screen_diagnostics)
                
                title = lvr.title(title_bar)
                title.set_text('Diagnostics')
                title.center()

                icon_back = lvr.button_icon(title_bar)
                icon_back.set_align(lv.ALIGN.LEFT_MID)
                icon_back.set_text('')
                icon_back.add_event_cb(lambda e: self.show_screen(self.screen_main), lv.EVENT_CODE.CLICKED, None)

                icon_refresh = lvr.button_icon(title_bar)
                icon_refresh.add_event_cb(lambda e: self.show_screen(self.screen_diagnostics), lv.EVENT_CODE.CLICKED, None)
                icon_refresh.set_text('')
                icon_refresh.set_align(lv.ALIGN.RIGHT_MID)

                self.screen_diagnostics.panel_diagnostics = lvr.panel(self.screen_diagnostics, flex_flow=lv.FLEX_FLOW.COLUMN)
                self.screen_diagnostics.panel_diagnostics.set_flex_grow(1)
                self.screen_diagnostics.panel_diagnostics.set_width(lv.pct(100))
                self.screen_diagnostics.panel_diagnostics.set_style_pad_all(0, lv.STATE.DEFAULT)
                self.screen_diagnostics.panel_diagnostics.set_style_pad_row(0, lv.STATE.DEFAULT)

        with lvr.lock():
            self.modal_tool = lvr.modal(self.root_modal, tag='modal_tool')
            if self.modal_tool:
                self.modal_tool.set_flex_flow(lv.FLEX_FLOW.COLUMN)
                self.modal_tool.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

                self.modal_tool.label_title = lvr.title(self.modal_tool)
                self.modal_tool.label_title.set_width(lv.pct(100))
                self.modal_tool.label_title.set_height(lvr.get_font_title().get_line_height())
                self.modal_tool.label_title.set_style_pad_bottom(lvr.get_global_margin(), lv.STATE.DEFAULT)
                self.modal_tool.label_title.set_long_mode(lv.LABEL_LONG_MODE.DOTS)
                self.modal_tool.label_title.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

                self.modal_tool.label_description = lvr.label(self.modal_tool)
                self.modal_tool.label_description.set_width(lv.pct(100))
                self.modal_tool.label_description.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                self.modal_tool.label_description.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

                panel_actions = lvr.panel(self.modal_tool)
                panel_actions.set_width(lv.pct(100))
                panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW)
                panel_actions.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                panel_actions.set_style_pad_column(lv.dpx(15), lv.STATE.DEFAULT)
                panel_actions.set_style_pad_all(0, lv.STATE.DEFAULT)
                panel_actions.set_style_pad_top(lvr.get_global_margin(), lv.STATE.DEFAULT)

                self.modal_tool.button_cancel = lvr.button(panel_actions)
                self.modal_tool.button_cancel.set_width(lv.pct(45))
                self.modal_tool.button_cancel.set_text('Cancel')
                self.modal_tool.button_cancel.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
                
                self.modal_tool.button_action = lvr.button(panel_actions)
                self.modal_tool.button_action.set_width(lv.pct(45))
                self.modal_tool.button_action.set_text('Download')

        with lvr.lock():
            self.modal_diagnostic = lvr.modal(self.root_modal, tag='modal_diagnostic')
            if self.modal_diagnostic:
                self.modal_diagnostic.set_flex_flow(lv.FLEX_FLOW.COLUMN)
                self.modal_diagnostic.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

                self.modal_diagnostic.label_title = lvr.title(self.modal_diagnostic)
                self.modal_diagnostic.label_title.set_style_pad_bottom(lvr.get_global_margin(), lv.STATE.DEFAULT)
                self.modal_diagnostic.label_title.set_width(lv.pct(100))
                self.modal_diagnostic.label_title.set_long_mode(lv.LABEL_LONG_MODE.SCROLL)
                self.modal_diagnostic.label_title.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

                self.modal_diagnostic.label_description = lvr.label(self.modal_diagnostic)
                self.modal_diagnostic.label_description.set_width(lv.pct(100))
                self.modal_diagnostic.label_description.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                self.modal_diagnostic.label_description.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)

                self.modal_diagnostic.label_fix = lvr.label(self.modal_diagnostic)
                self.modal_diagnostic.label_fix.set_width(lv.pct(100))
                self.modal_diagnostic.label_fix.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                self.modal_diagnostic.label_fix.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)
                self.modal_diagnostic.label_fix.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)

                panel_actions = lvr.panel(self.modal_diagnostic)
                panel_actions.set_width(lv.pct(100))
                panel_actions.set_flex_flow(lv.FLEX_FLOW.ROW)
                panel_actions.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
                panel_actions.set_style_pad_column(lv.dpx(15), lv.STATE.DEFAULT)
                panel_actions.set_style_pad_all(0, lv.STATE.DEFAULT)
                panel_actions.set_style_pad_top(lvr.get_global_margin(), lv.STATE.DEFAULT)

                self.modal_diagnostic.button_cancel = lvr.button(panel_actions)
                self.modal_diagnostic.button_cancel.set_width(lv.pct(45))
                self.modal_diagnostic.button_cancel.set_text('Cancel')
                self.modal_diagnostic.button_cancel.add_event_cb(lambda e: self.hide_modal(), lv.EVENT_CODE.CLICKED, None)
                
                self.modal_diagnostic.button_action = lvr.button(panel_actions)
                self.modal_diagnostic.button_action.set_width(lv.pct(45))
                self.modal_diagnostic.button_action.set_text('Download')

    def preload(self):
        import requests
        # self.cache_rinkhals_latest = Rinkhals.get_latest_version()
        # self.cache_rinkhals_available = Rinkhals.get_available_versions(False)
        # self.cache_firmware_latest = Firmware.get_latest_version()
        # self.cache_firmware_available = Firmware.get_available_versions()

    def show_screen(self, screen):
        super().show_screen(screen)

        if screen == self.screen_main: self.show_main()
        elif screen == self.screen_diagnostics: self.show_diagnostics()
    def show_main(self, force=False):
        def collect_diagnostics(force):
            if force or not self.diagnostics_cache:
                self.diagnostics_cache = list(Diagnostic.collect())

            lv.lock()

            color_info = lv.color_make(0, 160, 0)
            color_warning = lv.color_make(120, 120, 0)
            color_error = lv.color_make(160, 0, 0)

            diagnostics = self.diagnostics_cache
            if len(diagnostics) > 3:
                type_max = max([ d.type.value for d in diagnostics ])
                diagnostics = [ Diagnostic(DiagnosticType(type_max), f'{len(diagnostics)} diagnostics', '', '') ]

            self.screen_logo.panel_tags.clean()
            for d in diagnostics:
                tag = lvr.tag(self.screen_logo.panel_tags)

                if d.type == DiagnosticType.INFO:
                    tag.set_icon('')
                    tag.set_color(color_info)
                elif d.type == DiagnosticType.WARNING:
                    tag.set_icon('')
                    tag.set_color(color_warning)
                elif d.type == DiagnosticType.ERROR:
                    tag.set_icon('')
                    tag.set_color(color_error)

                if d.icon:
                    tag.set_icon(d.icon)
                tag.set_text(d.short_text)

                if d.fix_action:
                    tag.add_event_cb(lambda e, d=d: self.show_diagnostic_modal(d), lv.EVENT_CODE.CLICKED, None)
                else:
                    tag.add_event_cb(lambda e: self.show_screen(self.screen_diagnostics), lv.EVENT_CODE.CLICKED, None)

            if len(diagnostics) == 0:
                tag = lvr.tag(self.screen_logo.panel_tags)
                tag.set_icon('')
                tag.set_text('Everything is awesome')
                tag.set_color(color_info)

            lv.unlock()

        run_async(lambda force=force: collect_diagnostics(force))
    def show_diagnostics(self):
        def refresh_diagnostics():
            self.diagnostics_cache = list(Diagnostic.collect())

            lv.lock()
            self.screen_diagnostics.panel_diagnostics.clean()
            lv.unlock()

            if not self.diagnostics_cache:
                lv.lock()
                panel_text = lvr.panel(self.screen_diagnostics.panel_diagnostics)
                panel_text.set_size(lv.pct(100), lv.dpx(150))

                label_text = lvr.label(panel_text)
                label_text.set_text('No issues have been found on your printer')
                label_text.set_style_text_color(lvr.COLOR_DISABLED, lv.STATE.DEFAULT)
                label_text.set_width(lv.pct(80))
                label_text.set_align(lv.ALIGN.CENTER)
                label_text.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.STATE.DEFAULT)
                label_text.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                lv.unlock()

                return

            for d in self.diagnostics_cache:
                lv.lock()

                panel_diagnostic = lvr.panel(self.screen_diagnostics.panel_diagnostics)
                panel_diagnostic.set_width(lv.pct(100))
                panel_diagnostic.set_style_min_height(lv.dpx(72), lv.STATE.DEFAULT)
                panel_diagnostic.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.STATE.DEFAULT)

                label_description = lvr.label(panel_diagnostic)
                label_description.set_text(d.short_text)
                label_description.set_width(lv.pct(60))
                label_description.set_align(lv.ALIGN.LEFT_MID)
                label_description.set_long_mode(lv.LABEL_LONG_MODE.WRAP)
                
                if d.type == DiagnosticType.INFO:
                    color = lv.color_make(0, 180, 0)
                    icon = ''
                    text = 'Info'
                elif d.type == DiagnosticType.WARNING:
                    color = lv.color_make(180, 160, 0)
                    icon = ''
                    text = 'Warning'
                elif d.type == DiagnosticType.ERROR:
                    color = lv.color_make(180, 0, 0)
                    icon = ''
                    text = 'Error'

                tag_type = lvr.tag(panel_diagnostic)
                tag_type.set_align(lv.ALIGN.RIGHT_MID)
                tag_type.remove_flag(lv.OBJ_FLAG.CLICKABLE)
                tag_type.set_color(color)
                tag_type.set_icon(icon)
                tag_type.set_text(text)

                if d.fix_action:
                    panel_diagnostic.set_state(lv.STATE.DISABLED, False)
                    panel_diagnostic.add_event_cb(lambda e, d=d: self.show_diagnostic_modal(d), lv.EVENT_CODE.CLICKED, None)

                lv.unlock()

        run_async(refresh_diagnostics)
    def show_tool_modal(self, tool: Tool):
        def run_tool(tool=tool):
            lv.lock()
            self.modal_tool.button_cancel.set_state(lv.STATE.DISABLED, True)
            self.modal_tool.button_action.set_state(lv.STATE.DISABLED, True)
            lv.unlock()

            try:
                logging.info(f'Starting tool {tool.name}...')
                tool_path = os.path.join(TOOLS_PATH, tool.command)
                result = shell(tool_path)
                logging.info(f'Tool exited with code {result}')
            except:
                if USING_SIMULATOR:
                    time.sleep(2)
                pass

            lv.lock()
            self.modal_tool.button_cancel.set_state(lv.STATE.DISABLED, False)
            self.modal_tool.button_action.set_state(lv.STATE.DISABLED, False)
            lv.unlock()

        self.modal_tool.label_title.set_text(tool.name)
        self.modal_tool.label_description.set_text(tool.description)

        self.modal_tool.button_action.set_style_text_color(tool.action_color or lvr.COLOR_TEXT, lv.STATE.DEFAULT)
        self.modal_tool.button_action.set_text(tool.action or 'Run')
        self.modal_tool.button_action.clear_event_cb()
        self.modal_tool.button_action.add_event_cb(lambda e: run_async(run_tool), lv.EVENT_CODE.CLICKED, None)

        self.show_modal(self.modal_tool)
    def show_diagnostic_modal(self, diagnostic: Diagnostic):
        self.modal_diagnostic.label_title.set_text(diagnostic.short_text)
        self.modal_diagnostic.label_description.set_text(diagnostic.long_text)

        fix_cb = None

        if diagnostic.fix_action == DiagnosticFixes.RESET_CONFIGURATION:
            fix_text = 'Reset Rinkhals configuration to default. Your customizations will be backup up on the attached USB drive.'
            fix_action = 'Reset'
            def fix_cb(e):
                self.hide_modal()
                self.show_tool_modal(tool_reset_config)
        elif diagnostic.fix_action == DiagnosticFixes.REINSTALL_RINKHALS:
            fix_text = 'Reinstall Rinkhals. Your customizations will be kept.'
            fix_action = 'Reinstall'
            def fix_cb(e):
                self.hide_modal()
                self.show_screen(self.screen_ota_rinkhals)
        elif diagnostic.fix_action == DiagnosticFixes.REINSTALL_RINKHALS_LAUNCHER:
            fix_text = 'Patch Kobra startup to install Rinkhals launcher.'
            fix_action = 'Patch'
            def fix_cb(e):
                if os.path.exists('/useremain/rinkhals/.version'):
                    if os.path.exists('/userdata/app/gk/start.sh'):
                        with open('/userdata/app/gk/start.sh', 'r') as f:
                            script_content = f.read()
                            if 'Rinkhals/begin' not in script_content:
                                system(f'cat {SCRIPT_PATH}/start.sh.patch >> /userdata/app/gk/start.sh')
                    if os.path.exists('/userdata/app/gk/restart_k3c.sh'):
                        system(f'cat {SCRIPT_PATH}/start.sh.patch >> /userdata/app/gk/restart_k3c.sh')
                self.hide_modal()
                self.layout_main(force=True)
                self.layout_diagnostics()
        elif diagnostic.fix_action == DiagnosticFixes.REINSTALL_FIRMWARE:
            fix_text = 'Reinstall system firmware. Rinkhals will be re-enabled. Your customizations will be kept.'
            fix_action = 'Reinstall'
            def fix_cb(e):
                self.hide_modal()
                self.show_screen(self.screen_ota_firmware)
        elif diagnostic.fix_action and callable(diagnostic.fix_action):
            fix_text = diagnostic.fix_text or 'Run custom fix'
            fix_action = 'Fix'
            def fix_cb(e):
                diagnostic.fix_action()
                self.hide_modal()
                self.layout_main(True)

        self.modal_diagnostic.label_fix.set_text('Fix: ' + fix_text)

        self.modal_diagnostic.button_action.set_style_text_color(lvr.COLOR_DANGER, lv.STATE.DEFAULT)
        self.modal_diagnostic.button_action.set_text(fix_action)

        self.modal_diagnostic.button_action.clear_event_cb()
        if fix_cb:
            self.modal_diagnostic.button_action.add_event_cb(fix_cb, lv.EVENT_CODE.CLICKED, None)

        self.show_modal(self.modal_diagnostic)

if __name__ == '__main__':
    app = RinkhalsInstallApp()
    app.run()
