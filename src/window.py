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

from gi.repository import GObject, Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/window.ui')
class HatchetWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HatchetWindow'

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

    content = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        run_async(self._init())

    async def _init(self):
        foundry = await item_future(self.context.foundry)
        text_mgr = foundry.dup_text_manager()
        document = await text_mgr.load(
            Gio.File.new_for_path('/home/kol/hey.txt'),
            Foundry.Operation.new(),
            None,
        ).to_asyncio()
