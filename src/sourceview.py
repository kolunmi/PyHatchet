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

from gi.repository import GLib, GObject, Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/sourceview.ui')
class HatchetSourceView(Adw.Bin):
    __gtype_name__ = 'HatchetSourceView'

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

    content = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        action_group = Gio.SimpleActionGroup.new()
        self.create_action(action_group, "prev-line", self.action_prev_line, None)
        self.create_action(action_group, "next-line", self.action_next_line, None)
        self.create_action(action_group, "prev-char", self.action_prev_char, None)
        self.create_action(action_group, "next-char", self.action_next_char, None)
        self.create_action(action_group, "prev-word", self.action_prev_word, None)
        self.create_action(action_group, "next-word", self.action_next_word, None)
        self.insert_action_group("sourceview", action_group)

        shortcut_controller = Gtk.ShortcutController.new_for_model(self.context.sourceview_shortcuts_model)
        self.add_controller(shortcut_controller)

    def action_prev_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_line()
        buffer.place_cursor(iter)

    def action_next_line(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_line()
        buffer.place_cursor(iter)

    def action_prev_char(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_cursor_position()
        buffer.place_cursor(iter)

    def action_next_char(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_cursor_position()
        buffer.place_cursor(iter)

    def action_prev_word(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.backward_visible_word_start()
        buffer.place_cursor(iter)

    def action_next_word(self, action_name, params):
        if not self.sourceview:
            return
        buffer = self.sourceview.props.buffer
        mark = buffer.get_insert()
        iter = buffer.get_iter_at_mark(mark)
        iter.forward_visible_word_end()
        buffer.place_cursor(iter)

    def create_action(self, group, name, callback, params):
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        group.add_action(action)

    def do_grab_focus(self):
        if not self.sourceview:
            return
        self.sourceview.grab_focus()

    def open_document(self, document):
        self.sourceview = FoundryGtk.SourceView.new(document)
        self.content.set_child(self.sourceview)
