# picker.py
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
import os
from pathlib import Path

from gi.repository import GLib, GObject, Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/picker.ui')
class HatchetPicker(Adw.Bin):
    __gtype_name__ = 'HatchetPicker'

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

    selection_made = GObject.Signal(
        name="selection-made",
        flags=GObject.SignalFlags.RUN_FIRST,
        return_type=None,
        arg_types=[GObject.Object]
    )

    text_entry = Gtk.Template.Child()
    selection = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.action = None
        self.arg_hint = None
        self._build_selection()

    def _build_actions(self):
        app = Gio.Application.get_default()
        actions = app.list_actions()
        self.actions_model = Gtk.StringList.new(actions)
        self.selection.set_model(self.actions_model)

    def _build_files(self):
        text = self.text_entry.get_text()
        path = Path(text)

        try:
            files = os.listdir(path)
        except FileNotFoundError:
            try:
                files = os.listdir(path.parent)
            except:
                files = None
        except PermissionError:
            files = None
        except NotADirectoryError:
            files = None

        self.actions_model = Gtk.StringList.new(files)
        self.selection.set_model(self.actions_model)

    def _build_selection(self):
        if self.arg_hint:
            match self.arg_hint:
                case Gio.File:
                    self._build_files()
        else:
            self._build_actions()

    def _select(self, pos):
        if pos >= self.selection.props.n_items:
            return

        text = self.text_entry.get_text()

        app = Gio.Application.get_default()
        input = self.actions_model[pos].get_string()

        ret_object = None
        if self.arg_hint:
            match self.arg_hint:
                case Gio.File:
                    ret_object = Gio.File.new_for_path(Path(text, input))
        else:
            self.action = app.lookup_action(input)
            try:
                self.arg_hint = self.action._arg_hint
                if self.arg_hint:
                    self._build_selection()
                    return
            except Exception:
                pass

        if self.action:
            if isinstance(ret_object, Gio.File):
                variant = GLib.Variant("s", ret_object.get_path())
            else:
                variant = None
            self.action.activate(variant)
            self.emit("selection-made", ret_object)

        self.action = None
        self.arg_hint = None

    @Gtk.Template.Callback()
    def _text_changed_cb(self, text):
        self._build_selection()

    @Gtk.Template.Callback()
    def _text_activated_cb(self, text):
        self._select(self.selection.props.selected)

    @Gtk.Template.Callback()
    def _activated_cb(self, list_view, pos):
        self._select(self.selection.props.selected)
