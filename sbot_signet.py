import os
import json
import sublime
import sublime_plugin
from . import sbot_common as sc

# Definitions.
SIGNET_REGION_NAME = 'signet_region'
SIGNET_ICON = 'Packages/Theme - Default/common/label.png'
SIGNET_FILE_EXT = '.sigs'
SIGNET_SETTINGS_FILE = "SbotSignet.sublime-settings"

# The current signet collections. This is global across all ST instances/window/project.
# Key is current window id, value is the collection of file/line signet locations.
_sigs = {}


#-----------------------------------------------------------------------------------
def plugin_loaded():
    ''' Called once per plugin instance. '''
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    ''' Called once per plugin instance. '''
    pass


#-----------------------------------------------------------------------------------
class SignetEvent(sublime_plugin.EventListener):
    ''' Listener for view specific events of interest. '''

    # Need to track what's been initialized.
    _views_inited = set()
    _store_fn = None

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Load the persistence file. Views are valid.
        Note that this also happens if this module is reloaded - like when editing this file. '''
        settings = sublime.load_settings(SIGNET_SETTINGS_FILE)
        sc.set_log_level(settings.get('log_level'))

        if len(views) > 0:
            view = views[0]
            w = view.window()
            if w is not None: # view.window() is None here sometimes.
                project_fn = w.project_file_name()
                self._store_fn = sc.get_store_fn_for_project(project_fn, SIGNET_FILE_EXT)
                self._open_sigs(w)
                for view in views:
                    self._init_view(view)

    def on_load_project(self, window):
        ''' This gets called for new windows but not for the first one. '''
        self._open_sigs(window)
        for view in window.views():
            self._init_view(view)

    def on_pre_close_project(self, window):
        ''' Save to file when closing window/project. Seems to be called twice. '''
        self._save_sigs(window)

    def on_load(self, view):
        ''' Load a file. '''
        self._init_view(view)

    def on_pre_close(self, view):
        ''' This happens after on_pre_close_project() Get the current sigs for the view. '''
        # Window is still valid here.
        self._collect_sigs(view)

    def on_deactivated(self, view):
        # Window is still valid here.
        self._collect_sigs(view)

    def on_close(self, view):
        pass

    def _init_view(self, view):
        ''' Lazy init. '''
        fn = view.file_name()
        if view.is_scratch() is False and fn is not None:
            # Init the view if not already.
            vid = view.id()
            if vid not in self._views_inited:
                self._views_inited.add(vid)

                # Init the view with any persisted values.
                rows = None  # Default
                winid = view.window().id()
                fn = view.file_name()
                if winid in _sigs:
                    if fn in _sigs[winid]:
                        rows = _sigs[winid][fn]

                if rows is not None:
                    # Update visual signets, brutally. This is the ST way.
                    regions = []
                    for r in rows:
                        pt = view.text_point(r - 1, 0)  # ST is 0-based
                        regions.append(sublime.Region(pt, pt))
                    settings = sublime.load_settings(SIGNET_SETTINGS_FILE)
                    view.add_regions(SIGNET_REGION_NAME, regions, settings.get('scope'), SIGNET_ICON)

    def _open_sigs(self, window):
        ''' General project opener. '''
        winid = window.id()
        # project_fn = window.project_file_name()

        if self._store_fn is not None:
            winid = window.id()

            if os.path.isfile(self._store_fn):
                with open(self._store_fn, 'r') as fp:
                    values = json.load(fp)
                    _sigs[winid] = values
            else:
                # Assumes new file.
                sublime.status_message('Creating new signets file')
                _sigs[winid] = {}

    def _save_sigs(self, window):
        ''' General project saver. '''
        if self._store_fn is not None:
            winid = window.id()

            # Remove invalid files and any empty values.
            # Safe iteration - accumulate elements to del later.
            del_els = []

            win_sigs = _sigs[window.id()]

            for fn, _ in win_sigs.items():
                if fn is not None:
                    if not os.path.exists(fn):
                        del_els.append((winid, fn))
                    elif len(win_sigs[fn]) == 0:
                        del_els.append((winid, fn))

            # Now remove from collection.
            for (winid, fn) in del_els:
                del _sigs[winid][fn]

            # Update the signets as they may have moved during editing.
            for view in window.views():
                self._collect_sigs(view)

            # Now save, or delete if empty.
            if len(win_sigs) > 0:
                with open(self._store_fn, 'w') as fp:
                    json.dump(win_sigs, fp, indent=4)
            elif os.path.isfile(self._store_fn):
                os.remove(self._store_fn)

    def _collect_sigs(self, view):
        ''' Update the signets as they may have moved during editing. '''

        fn = view.file_name()
        window = view.window()

        if fn is not None and window is not None and window.id() in _sigs:
            win_sigs = _sigs[window.id()]
            regions = view.get_regions(SIGNET_REGION_NAME)

            if len(regions) > 0:
                if fn in win_sigs:
                    win_sigs[fn].clear()
                else:
                    win_sigs[fn] = []
                for reg in regions:
                    row, col = view.rowcol(reg.a)
                    win_sigs[fn].append(row + 1)
            else:
                try:
                    win_sigs.delete(fn)
                except:
                    pass


#-----------------------------------------------------------------------------------
class SbotToggleSignetCommand(sublime_plugin.TextCommand):
    ''' Flip the signet. '''

    def is_visible(self):
        ''' Don't allow signets in temp views. '''
        return self.view.is_scratch() is False and self.view.file_name() is not None

    def run(self, edit):
        # Get current row.
        caret = sc.get_single_caret(self.view)
        if caret is None:
            return  # -- early return

        sel_row, _ = self.view.rowcol(caret)

        drows = _get_view_signet_rows(self.view)

        if sel_row != -1:
            # Is there one currently at the selected row?
            existing = sel_row in drows
            if existing:
                drows.remove(sel_row)
            else:
                drows.append(sel_row)

        # Update collection.
        crows = None  # Default
        winid = self.view.window().id()
        fn = self.view.file_name()

        if winid in _sigs:
            if fn not in _sigs[winid]:
                # Add a new one.
                _sigs[winid][fn] = []

        if crows is not None:
            crows.clear()
            for r in drows:
                crows.append(r + 1)

        # Update visual signets, brutally. This is the ST way.
        regions = []
        for r in drows:
            pt = self.view.text_point(r, 0)  # 0-based
            regions.append(sublime.Region(pt, pt))

        settings = sublime.load_settings(SIGNET_SETTINGS_FILE)
        self.view.add_regions(SIGNET_REGION_NAME, regions, settings.get('scope'), SIGNET_ICON)


#-----------------------------------------------------------------------------------
class SbotGotoSignetCommand(sublime_plugin.TextCommand):
    ''' Navigate to next/prev signet in whole collection. '''

    def run(self, edit, where):
        ''' Common navigate to signet in whole collection. '''
        next = where == 'next'

        view = self.view
        window = view.window()
        winid = window.id()

        if winid not in _sigs:
            return  # --- early return

        settings = sublime.load_settings(SIGNET_SETTINGS_FILE)
        nav_files = settings.get('nav_files')

        done = False

        caret = sc.get_single_caret(view)
        if caret is None:
            return  # -- early return

        sel_row, _ = view.rowcol(caret)  # current selected row
        incr = +1 if next else -1
        array_end = 0 if next else -1

        # 1) next: If there's another bookmark below -> goto it
        # 1) prev: If there's another bookmark above -> goto it
        if not done:
            sig_rows = _get_view_signet_rows(view)
            if not next:
                sig_rows.reverse()
            for sr in sig_rows:
                if (next and sr > sel_row) or (not next and sr < sel_row):
                    view.run_command("goto_line", {"line": sr + 1})
                    done = True
                    break

            # At begin or end. Check for single file operation.
            if not done and not nav_files and len(sig_rows) > 0:
                view.run_command("goto_line", {"line": sig_rows[0] + 1})
                done = True

        # 2) next: Else if there's an open signet file to the right of this tab -> focus tab, goto first signet
        # 2) prev: Else if there's an open signet file to the left of this tab -> focus tab, goto last signet
        if not done:
            view_index = window.get_view_index(view)[1] + incr
            while not done and ((next and view_index < len(window.views()) or (not next and view_index >= 0))):
                vv = window.views()[view_index]
                sig_rows = _get_view_signet_rows(vv)
                if len(sig_rows) > 0:
                    window.focus_view(vv)
                    vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                    done = True
                else:
                    view_index += incr

        # 3) next: Else if there is a signet file in the project that is not open -> open it, focus tab, goto first signet
        # 3) prev: Else if there is a signet file in the project that is not open -> open it, focus tab, goto last signet
        if not done:
            winid = window.id()

            for fn, rows in _sigs[winid].items():
                if fn is not None:
                    if window.find_open_file(fn) is None and os.path.exists(fn) and len(rows) > 0:
                        vv = sc.wait_load_file(window, fn, rows[array_end])
                        # vv = window.open_file(fn)
                        # endrow = rows[array_end]
                        # sublime.set_timeout(lambda r=endrow: wait_load_file(vv, r), 10)  # already 1-based in file
                        # window.focus_view(vv)
                        done = True
                        break

        # 4) next: Else -> find first tab/file with signets, focus tab, goto first signet
        # 4) prev: Else -> find last tab/file with signets, focus tab, goto last signet
        if not done:
            view_index = 0 if next else len(window.views()) - 1
            while not done and ((next and view_index < len(window.views()) or (not next and view_index >= 0))):
                vv = window.views()[view_index]
                sig_rows = _get_view_signet_rows(vv)
                if len(sig_rows) > 0:
                    window.focus_view(vv)
                    vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                    done = True
                else:
                    view_index += incr


#-----------------------------------------------------------------------------------
class SbotClearAllSignetsCommand(sublime_plugin.TextCommand):
    ''' Clear all signets. '''

    def run(self, edit):
        # Clear collection for current window only.
        winid = self.view.window().id()
        if winid in _sigs:
            _sigs[winid] = {}

        # Clear visuals in open views.
        for vv in self.view.window().views():
            vv.erase_regions(SIGNET_REGION_NAME)


#-----------------------------------------------------------------------------------
def _get_view_signet_rows(view):
    ''' Get all the signet row numbers in the view. Returns a sorted list. '''
    sig_rows = []
    for reg in view.get_regions(SIGNET_REGION_NAME):
        row, _ = view.rowcol(reg.a)
        sig_rows.append(row)
    sig_rows.sort()
    return sig_rows
