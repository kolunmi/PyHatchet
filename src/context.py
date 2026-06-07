# context.py
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

from pathlib import Path

from gi.repository import GObject, Gio, Gtk, Foundry

from .util import run_async, item_future

class HatchetShortcuts(GObject.Object):
    __gtype_name__ = __qualname__

    window = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)
    picker = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)
    sourceview = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)
    form = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def new_with_stores():
        return HatchetShortcuts(
            window=Gio.ListStore.new(Gtk.Shortcut),
            picker=Gio.ListStore.new(Gtk.Shortcut),
            sourceview=Gio.ListStore.new(Gtk.Shortcut),
            form=Gio.ListStore.new(Gtk.Shortcut),
        )

    def apply(self, other):
        def copy(dest, src):
            dest.splice(0, len(dest), src)
        copy(self.window, other.window)
        copy(self.picker, other.picker)
        copy(self.sourceview, other.sourceview)
        copy(self.form, other.form)

class HatchetContext(GObject.Object):
    __gtype_name__ = __qualname__

    shortcuts = GObject.Property(type=HatchetShortcuts, default=None, flags=GObject.ParamFlags.READWRITE)
    user_foundry = GObject.Property(type=Foundry.FutureItem, default=None, flags=GObject.ParamFlags.READWRITE)
    foundrys = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)

    current_keymap = GObject.Property(type=str, default=None, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def list_documents(self):
        ret = []

        for future_item in self.foundrys:
            foundry = await item_future(future_item)
            text_mgr = foundry.dup_text_manager()
            documents = text_mgr.list_documents()
            ret += documents

        return ret

    async def get_foundry_for_path(self, path):
        for future_item in self.foundrys:
            if future_item == self.user_foundry:
                continue
            foundry = await item_future(future_item)
            project_directory = foundry.props.project_directory
            if not project_directory:
                continue
            project_directory_path = Path(project_directory.get_path())
            parent_path = Path(path)
            while parent_path != Path('/'):
                if parent_path == project_directory_path:
                    return foundry, foundry.props.project_directory.get_path().replace("/", "%")
                parent_path = parent_path.parent

        try:
            discover = await Foundry.Context.discover(path, None)
            construct_future = Foundry.Context.new(
                discover,
                None,
                Foundry.ContextFlags.CREATE,
                None,
            )
            self.foundrys.append(Foundry.FutureItem.new(construct_future))
            foundry = await construct_future
            return foundry, foundry.props.project_directory.get_path().replace("/", "%")
        except Exception:
            return await item_future(self.user_foundry), "USER"

class HatchetDocumentContext(GObject.Object):
    __gtype_name__ = __qualname__

    document = GObject.Property(type=Foundry.TextDocument, default=None, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    foundry = GObject.Property(type=Foundry.Context, default=None, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    git = GObject.Property(type=Foundry.Vcs, default=None, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    have_git = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)

    current_blame_signature = GObject.Property(type=Foundry.VcsSignature, default=None, flags=GObject.ParamFlags.READWRITE)
    have_current_blame_signature = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
