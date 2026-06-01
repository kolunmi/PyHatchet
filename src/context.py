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

from gi.repository import GObject, Gio, Foundry

from .util import run_async, item_future

class HatchetContext(GObject.Object):
    __gtype_name__ = 'HatchetContext'

    window_shortcuts_model = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)
    picker_shortcuts_model = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)
    sourceview_shortcuts_model = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)

    user_foundry = GObject.Property(type=Foundry.FutureItem, default=None, flags=GObject.ParamFlags.READWRITE)
    foundrys = GObject.Property(type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READWRITE)

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
                    return foundry
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
            return await construct_future
        except Exception:
            return await item_future(self.user_foundry)
