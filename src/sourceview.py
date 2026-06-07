# sourceview.py
#
# Copyright 2026 kol
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

from gi.repository import GLib, GObject, Gio, Gtk, Pango, Gdk, GtkSource, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext, HatchetDocumentContext

class FormNode:
    index = -1
    name = None
    value = None
    inner = None
    start_line = 0
    finish_line = 0
    folded = False

    def new(index=-1,
            name=None,
            value=None,
            inner=None,
            start_line=0,
            finish_line=0,
            folded=False,
            ):
        self = FormNode()
        self.index = index
        self.name = name
        self.value = value
        self.inner = inner
        self.start_line = start_line
        self.finish_line = finish_line
        self.folded = folded
        return self

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/sourceview.ui')
class HatchetSourceView(Adw.Bin):
    __gtype_name__ = __qualname__

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)
    document_ctx = GObject.Property(type=HatchetDocumentContext, default=None, flags=GObject.ParamFlags.READWRITE)

    content = Gtk.Template.Child()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        action_group = Gio.SimpleActionGroup.new()
        self.create_action(action_group, "cancel", self.action_cancel, None)
        self.create_action(action_group, "prev-line", self.action_prev_line, None)
        self.create_action(action_group, "next-line", self.action_next_line, None)
        self.create_action(action_group, "prev-char", self.action_prev_char, None)
        self.create_action(action_group, "next-char", self.action_next_char, None)
        self.create_action(action_group, "prev-word", self.action_prev_word, None)
        self.create_action(action_group, "next-word", self.action_next_word, None)
        self.create_action(action_group, "beginning-of-line", self.action_beginning_of_line, None)
        self.create_action(action_group, "end-of-line", self.action_end_of_line, None)
        self.create_action(action_group, "kill-word", self.action_kill_word, None)
        self.create_action(action_group, "backward-kill-word", self.action_backward_kill_word, None)
        self.create_action(action_group, "kill-line", self.action_kill_line, None)
        self.create_action(action_group, "kill-line-rest", self.action_kill_line_rest, None)
        self.create_action(action_group, "activate-mark-region", self.action_activate_mark_region, None)
        self.create_action(action_group, "copy-region", self.action_copy_region, None)
        self.create_action(action_group, "kill-region", self.action_kill_region, None)
        self.create_action(action_group, "paste", self.action_paste, None)
        self.create_action(action_group, "undo", self.action_undo, None)
        self.create_action(action_group, "insert-newline", self.action_insert_newline, None)
        self.create_action(action_group, "center-view", self.action_center_view, None)
        self.create_action(action_group, "scroll-up", self.action_scroll_up, None)
        self.create_action(action_group, "scroll-down", self.action_scroll_down, None)
        self.create_action(action_group, "next-pair", self.action_next_pair, None)
        self.create_action(action_group, "prev-pair", self.action_prev_pair, None)
        self.create_action(action_group, "mark-next-pair", self.action_mark_next_pair, None)
        self.create_action(action_group, "mark-prev-pair", self.action_mark_prev_pair, None)
        self.create_action(action_group, "swap-around-mark-region", self.action_swap_around_mark_region, None)
        self.create_action(action_group, "beginning-of-document", self.action_beginning_of_document, None)
        self.create_action(action_group, "end-of-document", self.action_end_of_document, None)
        self.insert_action_group("sourceview", action_group)
        shortcut_controller = Gtk.ShortcutController.new_for_model(self.context.shortcuts.sourceview)
        shortcut_controller.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self.add_controller(shortcut_controller)

        action_group = Gio.SimpleActionGroup.new()
        self.create_action(action_group, "next-item", self.action_form_next_item, None)
        self.create_action(action_group, "prev-item", self.action_form_prev_item, None)
        self.create_action(action_group, "toggle-fold", self.action_form_toggle_fold, None)
        self.insert_action_group("form", action_group)

        self.style_mgr = Adw.StyleManager.get_default()
        self.style_mgr.connect("notify::dark", self._dark_mode_changed_cb)

        self._reset(init=True)

    def do_dispose(self):
        self.style_mgr.disconnect_by_func(self._dark_mode_changed_cb)
        self._reset()
        super().do_dispose()

    def _reset(self, init=False):
        if not init:
            if self.document_ctx:
                self.document_ctx.props.current_blame_signature = None
                self.document_ctx.props.have_current_blame_signature = False

            if self.buffer:
                self.buffer.disconnect_by_func(self._contents_change_cb)
                self.buffer.disconnect_by_func(self._cursor_position_change_cb)

            if self.blame_update_routine:
                self.blame_update_routine.cancel()
            if self.blame_update_timeout > 0:
                GLib.Source.remove(self.blame_update_timeout)

            if self.form_shortcuts:
                self.remove_controller(self.form_shortcuts)


        self.overlay_cursor = None
        self.buffer = None
        self.last_insert_iter = None
        self.mark_region_iter = None
        self.blame = None
        self.blame_needs_update = False
        self.blame_update_routine = None
        self.blame_update_timeout = 0

        self.form = None
        self.form_ordered = None
        self.form_lines = None
        self.form_shortcuts = None
        self.form_highlight_bounds = None

    def _activate_mark_region(self):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        bound = buffer.get_selection_bound()
        insert_iter = buffer.get_iter_at_mark(insert)
        buffer.move_mark(bound, insert_iter)
        self.mark_region_iter = insert_iter

    def _deactivate_mark_region(self):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        bound = buffer.get_selection_bound()
        insert_iter = buffer.get_iter_at_mark(insert)
        buffer.move_mark(bound, insert_iter)
        self.mark_region_iter = None

    def _swap_around_mark_region(self):
        if not self.sourceview:
            return
        if not self.mark_region_iter:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert)
        bound = buffer.get_selection_bound()
        buffer.move_mark(insert, self.mark_region_iter)
        buffer.move_mark(bound, insert_iter)
        self.mark_region_iter = insert_iter

    def _stable_half_page_scroll(self, modifier):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        old_visible_rect = self.sourceview.get_visible_rect()
        old_iter = buffer.get_iter_at_mark(insert)
        old_location = self.sourceview.get_iter_location(old_iter)
        old_yoffset = old_location.y - old_visible_rect.y

        adjustment = self.content.props.vadjustment
        page_size = adjustment.props.page_size
        adjustment.props.value += (page_size / 2) * modifier

        new_visible_rect = self.sourceview.get_visible_rect()
        new_x = old_location.x
        new_y = new_visible_rect.y + old_yoffset

        _, new_iter = self.sourceview.get_iter_at_location(new_x, new_y)
        new_location = self.sourceview.get_iter_location(new_iter)
        new_yoffset = new_location.y - new_visible_rect.y
        adjustment.props.value += new_yoffset - old_yoffset

        buffer.place_cursor(new_iter)

    def _traverse_pair(self, backward=False):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert)
        if backward:
            insert_iter.backward_cursor_position()
        ch = insert_iter.get_char()
        valid_chs = [
            ("(", ")"),
            ("[", "]"),
            ("{", "}"),
            ("<", ">"),
        ]
        valid = False
        for test in valid_chs:
            if backward:
                right_ch, left_ch = test
            else:
                left_ch, right_ch = test
            if ch == left_ch:
                search_iter = insert_iter.copy()
                if not backward:
                    search_iter.forward_cursor_position()
                valid = True
                break
        if not valid:
            min_offset = None
            for test in valid_chs:
                if backward:
                    result = insert_iter.backward_search(test[1], Gtk.TextSearchFlags.TEXT_ONLY)
                else:
                    result = insert_iter.forward_search(test[0], Gtk.TextSearchFlags.TEXT_ONLY)
                if result:
                    start, end = result
                    offset = end.get_offset()
                    pick = False
                    if min_offset:
                        if backward:
                            pick = offset > min_offset
                        else:
                            pick = offset < min_offset
                    else:
                        pick = True
                    if pick:
                        min_offset = offset
                        if backward:
                            search_iter = start
                            right_ch, left_ch = test
                        else:
                            search_iter = end
                            left_ch, right_ch = test
                        valid = True
        if not valid:
            return
        stack_size = 1
        while stack_size > 0:
            if backward:
                left_result = search_iter.backward_search(left_ch, Gtk.TextSearchFlags.TEXT_ONLY)
            else:
                left_result = search_iter.forward_search(left_ch, Gtk.TextSearchFlags.TEXT_ONLY)
            if left_result:
                left_start, left_end = left_result
            else:
                left_start = None
                left_end = None
            if backward:
                right_result = search_iter.backward_search(right_ch, Gtk.TextSearchFlags.TEXT_ONLY)
            else:
                right_result = search_iter.forward_search(right_ch, Gtk.TextSearchFlags.TEXT_ONLY)
            if right_result:
                right_start, right_end = right_result
            else:
                right_start = None
                right_end = None
            if left_result and right_result:
                if backward:
                    cmp = right_start.compare(left_start)
                else:
                    cmp = left_start.compare(right_start)
                if cmp < 0:
                    if backward:
                        search_iter = left_start
                    else:
                        search_iter = left_end
                    stack_size += 1
                else:
                    if backward:
                        search_iter = right_start
                    else:
                        search_iter = right_end
                    stack_size -= 1
            elif right_result:
                if backward:
                    search_iter = right_start
                else:
                    search_iter = right_end
                stack_size -= 1
            else:
                break
        if stack_size > 0:
            return
        buffer.place_cursor(search_iter)
        self.sourceview.jump_to_iter(search_iter, 0.0, False, 0.0, 0.0)

    def action_cancel(self, action_name, params):
        if not self.sourceview:
            return
        self._deactivate_mark_region()

        toast_overlay = self.get_ancestor(Adw.ToastOverlay)
        if toast_overlay:
            toast_overlay.dismiss_all()

    def action_prev_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_line()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_next_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_line()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_prev_char(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_cursor_position()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_next_char(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_cursor_position()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_prev_word(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_word_start()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_next_word(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_word_end()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_beginning_of_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.set_line_index(0)
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_end_of_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_to_line_end()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_kill_word(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        end = buffer.get_iter_at_mark(mark)
        end.forward_visible_word_end()
        buffer.delete_interactive(start, end, True)

    def action_backward_kill_word(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        start.backward_visible_word_start()
        end = buffer.get_iter_at_mark(mark)
        buffer.delete_interactive(start, end, True)

    def action_kill_line(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        start.set_line_index(0)
        end = buffer.get_iter_at_mark(mark)
        end.forward_visible_line()
        buffer.delete_interactive(start, end, True)

    def action_kill_line_rest(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        end = buffer.get_iter_at_mark(mark)
        end.forward_to_line_end()
        buffer.delete_interactive(start, end, True)

    def action_activate_mark_region(self, action_name, params):
        self._activate_mark_region()

    def action_copy_region(self, action_name, params):
        if not self.sourceview:
            return
        if not self.mark_region_iter:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert)
        cmp = insert_iter.compare(self.mark_region_iter)
        if cmp > 0:
            start = self.mark_region_iter
            end = insert_iter
        else:
            start = insert_iter
            end = self.mark_region_iter
        text = start.get_text(end)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        self._deactivate_mark_region()

    def action_kill_region(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        if not self.mark_region_iter:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert)
        cmp = insert_iter.compare(self.mark_region_iter)
        if cmp > 0:
            start = self.mark_region_iter
            end = insert_iter
        else:
            start = insert_iter
            end = self.mark_region_iter
        text = start.get_text(end)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        self._deactivate_mark_region()
        buffer.delete_interactive(start, end, True)

    def action_paste(self, action_name, params):
        async def routine():
            if not self.sourceview or not self.sourceview.props.editable:
                return
            clipboard = Gdk.Display.get_default().get_clipboard()
            text = await clipboard.read_text_async()
            buffer = self.sourceview.props.buffer
            insert = buffer.get_insert()
            insert_iter = buffer.get_iter_at_mark(insert)
            buffer.insert(insert_iter, text)
            self._deactivate_mark_region()
        run_async(routine())

    def action_undo(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        buffer.undo()

    def action_insert_newline(self, action_name, params):
        if not self.sourceview or not self.sourceview.props.editable:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert)
        buffer.insert(insert_iter, "\n")

    def action_center_view(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        self.sourceview.scroll_to_mark(insert, 0.0, True, 0.0, 0.5)

    def action_scroll_up(self, action_name, params):
        self._stable_half_page_scroll(-1)

    def action_scroll_down(self, action_name, params):
        self._stable_half_page_scroll(1)

    def action_next_pair(self, action_name, params):
        self._traverse_pair()

    def action_prev_pair(self, action_name, params):
        self._traverse_pair(backward=True)

    def action_mark_next_pair(self, action_name, params):
        if not self.sourceview:
            return
        if not self.mark_region_iter:
            self._activate_mark_region()
        self._traverse_pair()

    def action_mark_prev_pair(self, action_name, params):
        if not self.sourceview:
            return
        if not self.mark_region_iter:
            self._activate_mark_region()
        self._traverse_pair(backward=True)

    def action_swap_around_mark_region(self, action_name, params):
        self._swap_around_mark_region()

    def action_beginning_of_document(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        iter = buffer.get_start_iter()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def action_end_of_document(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        iter = buffer.get_end_iter()
        buffer.place_cursor(iter)
        self.sourceview.jump_to_iter(iter, 0.0, False, 0.0, 0.0)

    def create_action(self, group, name, callback, params):
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        group.add_action(action)

    def _contents_change_cb(self, buffer):
        self.blame_needs_update = True

    def _cursor_position_change_cb(self, buffer, pspec):
        insert = buffer.get_insert()

        if self.last_insert_iter:
            if self.mark_region_iter:
                bound = buffer.get_selection_bound()
                buffer.move_mark(bound, self.mark_region_iter)

        self.last_insert_iter = buffer.get_iter_at_mark(insert)

        insert_iter = buffer.get_iter_at_mark(insert)
        insert_location = self.sourceview.get_iter_location(insert_iter)
        self.sourceview.move_overlay(self.overlay_cursor, insert_location.x, insert_location.y)
        self.overlay_cursor.props.width_request = max(insert_location.width, 4)
        self.overlay_cursor.props.height_request = insert_location.height

        if self.blame and not self.blame_update_routine:
            def idle():
                self.blame_update_timeout = 0
                if not self.blame:
                    return
                async def retrieve_blame():
                    if self.blame_needs_update:
                        bytes = GLib.Bytes.new(self.buffer.props.text.encode())
                        await self.blame.update(bytes)
                        self.blame_needs_update = False
                    if not self.blame:
                        self.blame_update_routine = None
                        return
                    buffer = self.sourceview.props.buffer
                    insert = buffer.get_insert()
                    insert_iter = buffer.get_iter_at_mark(insert)
                    line = insert_iter.get_line()
                    self.document_ctx.props.current_blame_signature = self.blame.query_line(line)
                    self.document_ctx.props.have_current_blame_signature = self.document_ctx.props.current_blame_signature is not None
                    self.blame_update_routine = None
                self.blame_update_routine = run_async(retrieve_blame())

            if self.blame_update_timeout > 0:
                GLib.Source.remove(self.blame_update_timeout)
                self.blame_update_timeout = 0
            if self.blame_needs_update:
                self.blame_update_timeout = GLib.timeout_add(1000, idle)
            else:
                idle()

        if self.form:
            self._highlight_form()

    def _dark_mode_changed_cb(self, style_manager, pspec):
        self._style_sourceview()

    def _style_sourceview(self):
        if not self.sourceview or not self.sourceview.props.buffer:
            return

        if self.style_mgr.props.dark:
            id = "Adwaita-dark"
        else:
            id = "Adwaita";

        style_scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        scheme = style_scheme_mgr.get_scheme(id)
        self.sourceview.props.buffer.props.style_scheme = scheme

    def _highlight_form(self):
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        line = iter.get_line()

        if self.form_highlight_bounds:
            start_line, finish_line = self.form_highlight_bounds
            _, start_iter = buffer.get_iter_at_line(start_line)
            _, end_iter = buffer.get_iter_at_line(finish_line)
            buffer.remove_tag_by_name("form-selected", start_iter, end_iter)
            self.form_highlight_bounds = None

        if line >= len(self.form_lines):
            return
        node = self.form_lines[line][0]

        _, start_iter = buffer.get_iter_at_line(node.start_line)
        _, end_iter = buffer.get_iter_at_line(node.finish_line)
        buffer.apply_tag_by_name("form-selected", start_iter, end_iter)
        self.form_highlight_bounds = (node.start_line, node.finish_line)

    def do_grab_focus(self):
        if not self.sourceview:
            return
        self.sourceview.grab_focus()

    def open_document(self, document_ctx):
        self._reset()

        self.document_ctx = document_ctx
        self.sourceview = FoundryGtk.SourceView.new(document_ctx.document)

        gutter = GtkSource.Gutter(view=self.sourceview)
        gutter.insert(FoundryGtk.ChangesGutterRenderer(), 0)

        self.overlay_cursor = Gtk.Fixed.new()
        self.overlay_cursor.add_css_class("overlay-cursor")
        self.sourceview.add_overlay(self.overlay_cursor, 0, 0)
        self.sourceview.props.cursor_visible = False

        # prevent the text-view's builtin key bindings from messing with ours
        #input_inhibit = Gtk.EventControllerKey.new()
        #def on_key_press(controller, keyval, keycode, state):
        #    return True
        #input_inhibit.connect("key-pressed", on_key_press)
        #self.sourceview.add_controller(input_inhibit)

        self.buffer = self.sourceview.props.buffer
        self.buffer.connect("changed", self._contents_change_cb)
        self.buffer.connect("notify::cursor-position", self._cursor_position_change_cb)
        self.buffer.create_tag(
            "form-key",
            weight=700,
        )
        self.buffer.create_tag(
            "form-struct-key",
            weight=700,
            underline=Pango.Underline.SINGLE,
        )
        self.buffer.create_tag(
            "form-selected",
            foreground="black",
            background="goldenrod",
            weight=600,
        )
        self._style_sourceview()
        self.content.set_child(self.sourceview)

        if self.document_ctx.git:
            async def make_blame():
                if not self.document_ctx.git:
                    return
                try:
                    vcs_file = await self.document_ctx.git.find_file(self.document_ctx.document.props.file)
                    self.blame = await self.document_ctx.git.blame(vcs_file)
                except:
                    self.blame = None
                self.blame_update_routine = None
            self.blame_update_routine = run_async(make_blame())

    def open_object_form(self, object):
        if not self.sourceview:
            return

        self.form = self._open_object_form_inner(object, 0)

        buffer = self.sourceview.props.buffer
        buffer.props.text = ""
        self.form_ordered = []
        self.form_lines = []
        self._render_form(buffer, self.form, 0)

        start_iter = buffer.get_start_iter()
        buffer.place_cursor(start_iter)
        self.sourceview.jump_to_iter(start_iter, 0.0, False, 0.0, 0.0)

        self.sourceview.props.editable = False
        if not self.form_shortcuts:
            self.form_shortcuts = Gtk.ShortcutController.new_for_model(self.context.shortcuts.form)
            self.form_shortcuts.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
            self.add_controller(self.form_shortcuts)

    def _open_object_form_inner(self, object, level, parents=set()):
        if object in parents:
            return None
        parents |= {object}

        if isinstance(object, Gio.ListModel):
            inner = []
            for item in object:
                recurse_inner = self._open_object_form_inner(item, level + 1, parents=parents)
                if recurse_inner:
                    inner.append(FormNode.new(value=item, inner=recurse_inner, folded=level>0))
                else:
                    parents |= {item}
            return inner
        else:
            inner = []
            props = object.list_properties()
            for prop in props:
                try:
                    value = object.get_property(prop.name)
                except:
                    continue
                if isinstance(value, GObject.Object):
                    recurse_inner = self._open_object_form_inner(value, level + 1, parents=parents)
                else:
                    if isinstance(value, GLib.DateTime):
                        recurse_inner = value.format("%x")
                    else:
                        recurse_inner = str(value)
                if recurse_inner:
                    inner.append(FormNode.new(name=prop.name, value=value, inner=recurse_inner, folded=isinstance(value, Gio.ListModel)))
                else:
                    parents |= {value}
            return inner

    def _render_form(self, buffer, form, level):
        for node in form:
            node.index = len(self.form_ordered)
            self.form_ordered.append(node)

            node.start_line = buffer.get_end_iter().get_line()
            if node.folded:
                if node.name:
                    buffer.insert(buffer.get_end_iter(), f"{node.name}/\n")
                else:
                    buffer.insert(buffer.get_end_iter(), f"/\n")
            else:
                if isinstance(node.inner, list):
                    if node.name:
                        buffer.insert_with_tags_by_name(buffer.get_end_iter(), f"{node.name}:", "form-struct-key")
                    else:
                        buffer.insert(buffer.get_end_iter(), f"-")
                    buffer.insert(buffer.get_end_iter(), "\n")
                    self._render_form(buffer, node.inner, level + 1)
                else:
                    if node.name:
                        buffer.insert_with_tags_by_name(buffer.get_end_iter(), f"{node.name}: ", "form-key")
                    buffer.insert(buffer.get_end_iter(), f"{node.inner}\n")
            if level == 0:
                buffer.insert(buffer.get_end_iter(), "\n")
            node.finish_line = buffer.get_end_iter().get_line()

            if node.start_line >= len(self.form_lines):
                for i in range(node.start_line - len(self.form_lines)):
                    self.form_lines.append([])
            for i in range(node.start_line, node.finish_line):
                if i >= len(self.form_lines):
                    self.form_lines.append([node])
                else:
                    self.form_lines[i].append(node)

    def _form_change_item(self, offset):
        if not self.form:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        line = iter.get_line()

        if line >= len(self.form_lines):
            return
        node = self.form_lines[line][0]
        if node.index + offset >= len(self.form_ordered):
            return
        new_node = self.form_ordered[node.index + offset]

        _, new_iter = buffer.get_iter_at_line(new_node.start_line)
        while new_iter.get_line() > 0 and new_iter.get_char() == "\n":
            if offset < 0:
                new_iter.backward_line()
            else:
                new_iter.forward_line()

        buffer.place_cursor(new_iter)
        self.sourceview.jump_to_iter(new_iter, 0.0, False, 0.0, 0.0)

    def action_form_next_item(self, action_name, params):
        self._form_change_item(1)

    def action_form_prev_item(self, action_name, params):
        self._form_change_item(-1)

    def action_form_toggle_fold(self, action_name, params):
        if not self.form:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        line = iter.get_line()

        if line >= len(self.form_lines):
            return

        node = self.form_lines[line][0]
        node.folded = not node.folded

        buffer.props.text = ""
        self.form_ordered = []
        self.form_lines = []
        self._render_form(buffer, self.form, 0)
        self.sourceview.props.vadjustment.emit("value-changed")

        _, new_iter = buffer.get_iter_at_line(node.start_line)
        buffer.place_cursor(new_iter)
        self.sourceview.scroll_to_iter(new_iter, 0.0, False, 0.0, 0.0)
        self.sourceview.props.vadjustment.emit("value-changed")
