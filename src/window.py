# window.py
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

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/window.ui')
class HatchetWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HatchetWindow'

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

    content = Gtk.Template.Child()
    action_picker = Gtk.Template.Child()
    picker_selection = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._build_actions()
        app = self.get_application()
        app.connect("action-added", self._build_actions)
        app.connect("action-removed", self._build_actions)

    def _build_actions(self):
        actions = self.get_application().list_actions()
        self.actions_model = Gtk.StringList.new(actions)
        self.picker_selection.set_model(self.actions_model)

    @Gtk.Template.Callback()
    def _picker_activated_cb(self, list_view, pos):
        app = self.get_application()
        action = self.actions_model[pos].get_string()
        variant = None
        app.activate_action(action, None)

    def open_document(self, document):
        source_view = FoundryGtk.SourceView.new(document)
        scrolled_window = Gtk.ScrolledWindow.new()
        scrolled_window.set_child(source_view)
        self.content.set_child(scrolled_window)
