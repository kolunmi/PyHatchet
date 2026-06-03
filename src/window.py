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
from .context import HatchetContext, HatchetDocumentContext
from .picker import HatchetPicker
from .sourceview import HatchetSourceView

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/window.ui')
class HatchetWindow(Adw.ApplicationWindow):
    __gtype_name__ = __qualname__

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)
    document_ctx = GObject.Property(type=HatchetDocumentContext, default=None, flags=GObject.ParamFlags.READWRITE)

    toasts = Gtk.Template.Child()
    overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.document_ctx = HatchetDocumentContext()

        action_group = Gio.SimpleActionGroup.new()
        self.create_action(action_group, "show-error", self.action_show_error, "(ss)")
        self.create_action(action_group, "open-action-picker", self.action_open_action_picker, "s")
        self.create_action(action_group, "save-document", self.action_save_document, None)
        self.insert_action_group("win", action_group)

        shortcut_controller = Gtk.ShortcutController.new_for_model(self.context.shortcuts.window)
        shortcut_controller.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self.add_controller(shortcut_controller)

        self.sourceview = HatchetSourceView(context=self.context)
        self.overlay.set_child(self.sourceview)

        self.picker = None

    def action_show_error(self, action_name, params):
        heading, body = params.unpack()
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "OK")
        dialog.props.default_response = "ok"
        dialog.present(self)

    def action_open_action_picker(self, action_name, params):
        if self.picker:
            return
        for_action = params.get_string()
        picker = HatchetPicker(
            context=self.context,
            for_action=for_action,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.START,
            margin_start=30,
            margin_end=30,
            margin_top=30,
            margin_bottom=30,
        )
        picker.connect("selection-made", self.picker_selection_made_cb)
        self.overlay.add_overlay(picker)
        self.picker = picker

    def action_save_document(self, action_name, params):
        if not self.document_ctx:
            return
        variant = GLib.Variant("s", self.document_ctx.document.props.file.get_path())
        self.activate_action('app.save-document', variant)

    def picker_selection_made_cb(self, ret_object, picker):
        if not self.picker:
            return
        self.overlay.remove_overlay(self.picker)
        self.picker = None

    def create_action(self, group, name, callback, params):
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        group.add_action(action)

    def _on_active_document_saved(self, document, file):
        basename = file.get_basename()
        toast = Adw.Toast(
            title=f"Wrote {basename}",
            timeout=1,
        )
        self.toasts.add_toast(toast)

    def open_document(self, document, foundry):
        if self.document_ctx and self.document_ctx.document:
            self.document_ctx.document.disconnect_by_func(self._on_active_document_saved)
        document.connect("saved", self._on_active_document_saved)

        git = foundry.props.vcs_manager.find_vcs("git")
        self.document_ctx = HatchetDocumentContext(
            document=document,
            foundry=foundry,
            git=git,
            have_git=git is not None,
        )

        self.sourceview.open_document(self.document_ctx)
        self.sourceview.grab_focus()

    @Gtk.Template.Callback()
    def _format_datetime(self, widget, datetime):
        return datetime.format("%x")
