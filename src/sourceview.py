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

from gi.repository import GLib, GObject, Gio, Gtk, Gdk, GtkSource, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/sourceview.ui')
class HatchetSourceView(Adw.Bin):
    __gtype_name__ = __qualname__

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

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
        self.insert_action_group("sourceview", action_group)

        shortcut_controller = Gtk.ShortcutController.new_for_model(self.context.shortcuts.sourceview)
        shortcut_controller.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self.add_controller(shortcut_controller)

        self.style_mgr = Adw.StyleManager.get_default()
        self.style_mgr.connect("notify::dark", self._dark_mode_changed_cb)

        self.buffer = None
        self.last_insert_iter = None
        self.mark_region_iter = None

    def do_dispose(self):
        self.style_mgr.disconnect_by_func("notify::dark", self._dark_mode_changed_cb)
        super().do_dispose()

    def _deactivate_mark_region(self):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        bound = buffer.get_selection_bound()
        insert_iter = buffer.get_iter_at_mark(insert)
        buffer.move_mark(bound, insert_iter)
        self.mark_region_iter = None

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

    def action_cancel(self, action_name, params):
        if not self.sourceview:
            return
        self._deactivate_mark_region()

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
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        end = buffer.get_iter_at_mark(mark)
        end.forward_visible_word_end()
        buffer.delete_interactive(start, end, True)

    def action_backward_kill_word(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        start.backward_visible_word_start()
        end = buffer.get_iter_at_mark(mark)
        buffer.delete_interactive(start, end, True)

    def action_kill_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        start.set_line_index(0)
        end = buffer.get_iter_at_mark(mark)
        end.forward_visible_line()
        buffer.delete_interactive(start, end, True)

    def action_kill_line_rest(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        start = buffer.get_iter_at_mark(mark)
        end = buffer.get_iter_at_mark(mark)
        end.forward_to_line_end()
        buffer.delete_interactive(start, end, True)

    def action_activate_mark_region(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        insert = buffer.get_insert()
        bound = buffer.get_selection_bound()
        insert_iter = buffer.get_iter_at_mark(insert)
        buffer.move_mark(bound, insert_iter)
        self.mark_region_iter = insert_iter

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
        buffer.delete_interactive(start, end, True)

    def action_paste(self, action_name, params):
        async def routine():
            if not self.sourceview:
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
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        buffer.undo()

    def action_insert_newline(self, action_name, params):
        if not self.sourceview:
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

    def create_action(self, group, name, callback, params):
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        group.add_action(action)

    def _dark_mode_changed_cb(self, style_manager, pspec):
        self._style_sourceview()

    def _cursor_position_change_cb(self, buffer, pspec):
        insert = buffer.get_insert()

        if self.last_insert_iter:
            if self.mark_region_iter:
                bound = buffer.get_selection_bound()
                buffer.move_mark(bound, self.mark_region_iter)

        self.last_insert_iter = buffer.get_iter_at_mark(insert)

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

    def do_grab_focus(self):
        if not self.sourceview:
            return
        self.sourceview.grab_focus()

    def open_document(self, document):
        if self.buffer:
            self.buffer.disconnect_by_func(self._cursor_position_change_cb)
        self.buffer = None
        self.last_insert_iter = None
        self.mark_region_iter = None

        self.sourceview = FoundryGtk.SourceView.new(document)
        gutter = GtkSource.Gutter(view=self.sourceview)
        gutter.insert(FoundryGtk.ChangesGutterRenderer(), 0)

        # prevent the text-view's builtin key bindings from messing with ours
        #input_inhibit = Gtk.EventControllerKey.new()
        #def on_key_press(controller, keyval, keycode, state):
        #    return True
        #input_inhibit.connect("key-pressed", on_key_press)
        #self.sourceview.add_controller(input_inhibit)

        self.buffer = self.sourceview.props.buffer
        self.buffer.connect("notify::cursor-position", self._cursor_position_change_cb)
        self._style_sourceview()
        self.content.set_child(self.sourceview)
