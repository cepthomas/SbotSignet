import os
import json
import pathlib
import sublime
import sublime_plugin

try:
    from SbotCommon.sbot_common import trace_function, trace_method, get_store_fn
except ModuleNotFoundError as e:
    sublime.message_dialog('SbotSignet plugin requires SbotCommon plugin')


# Definitions.
SIGNET_REGION_NAME = 'signet_region'
SIGNET_ICON = 'Packages/Theme - Default/common/label.png'
SIGNET_FILE_EXT = '.sbot-sigs'


# The current signet collections. This is global across all ST instances/window/project.
# Key is current window id, value is the collection of file/line signet locations.
_sigs = {}


#-----------------------------------------------------------------------------------
class SignetEvent(sublime_plugin.EventListener):
    ''' Listener for view specific events of interest. See lifecycle notes in README.md. '''

    # Need to track what's been initialized.
    views_inited = set()

    @trace_method
    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Load the persistence file. Views are valid.
        Note that this also happens if this module is reloaded - like when editing this file. '''
        view = views[0]
        self._open_sigs(view.window())
        for view in views:
            self._init_view(view)

    @trace_method
    def on_load_project(self, window):
        ''' This gets called for new windows but not for the first one. '''
        self._open_sigs(window)
        for view in window.views():
            self._init_view(view)

    @trace_method
    def on_pre_close_project(self, window):
        ''' Save to file when closing window/project. Seems to be called twice. '''
        self._save_sigs(window)

    @trace_method
    def on_load(self, view):
        ''' Load a file. '''
        self._init_view(view)

    @trace_method
    def on_pre_close(self, view):
        ''' This happens after on_pre_close_project() Get the current sigs for the view. '''
        self._collect_sigs(view)
        self._save_sigs(view.window())

    @trace_method
    def _init_view(self, view):
        ''' Lazy init. '''
        fn = view.file_name()
        if view.is_scratch() is False and fn is not None:
            # Init the view if not already.
            vid = view.id()
            if vid not in self.views_inited:
                self.views_inited.add(vid)

                # Init the view with any persist values.
                rows = _get_persist_rows(view, False)
                if rows is not None:
                    # Update visual signets, brutally. This is the ST way.
                    regions = []
                    for r in rows:
                        pt = view.text_point(r - 1, 0)  # ST is 0-based
                        regions.append(sublime.Region(pt, pt))
                    settings = sublime.load_settings("SbotSignet.sublime-settings")
                    view.add_regions(SIGNET_REGION_NAME, regions, settings.get('signet_scope'), SIGNET_ICON)

    @trace_method
    def _open_sigs(self, window):
        ''' General project opener. '''
        global _sigs

        winid = window.id()
        project_fn = window.project_file_name()

        if project_fn is not None:
            store_fn = get_store_fn(project_fn, SIGNET_FILE_EXT)

            if os.path.isfile(store_fn):
                with open(store_fn, 'r') as fp:
                    values = json.load(fp)
                    _sigs[winid] = values
            else:
                # Assumes new file.
                sublime.status_message('Creating new signets file')
                _sigs[winid] = {}

    @trace_method
    def _save_sigs(self, window):
        ''' General project saver. '''
        global _sigs

        winid = window.id()
        project_fn = window.project_file_name()

        if project_fn is not None and winid in _sigs:
            store_fn = get_store_fn(project_fn, SIGNET_FILE_EXT)

            # Remove invalid files and any empty values.
            # Safe iteration - accumulate elements to del later.
            del_els = []

            sigs = _sigs[window.id()]

            for fn, _ in sigs.items():
                if fn is not None:
                    if not os.path.exists(fn):
                        del_els.append((winid, fn))
                    elif len(sigs[fn]) == 0:
                        del_els.append((winid, fn))

            # Now remove from collection.
            for (w, fn) in del_els:
                del _sigs[w][fn]

            # Update the signets as they may have moved during editing.
            for view in window.views():
                self._collect_sigs(view)

            # Now save, or delete if empty.
            if len(sigs) > 0:
                with open(store_fn, 'w') as fp:
                    json.dump(sigs, fp, indent=4)
            elif os.path.isfile(store_fn):
                os.remove(store_fn)

    def _collect_sigs(self, view):
        ''' Update the signets as they may have moved during editing. '''
        fn = view.file_name()
        if(fn in _sigs):
            sigs[fn].clear()
            regions = view.get_regions(SIGNET_REGION_NAME)
            for reg in regions:
                row, col = view.rowcol(reg.a)
                sigs[fn].append(row + 1)

#-----------------------------------------------------------------------------------
class SbotToggleSignetCommand(sublime_plugin.TextCommand):
    ''' Flip the signet. '''

    def is_visible(self):
        ''' Don't allow signets in temp views. '''
        return self.view.is_scratch() is False and self.view.file_name() is not None

    def run(self, edit):
        # Get current row.
        sel_row, _ = self.view.rowcol(self.view.sel()[0].a)

        drows = _get_display_signet_rows(self.view)

        if sel_row != -1:
            # Is there one currently at the selected row?
            existing = sel_row in drows
            if existing:
                drows.remove(sel_row)
            else:
                drows.append(sel_row)

        # Update collection.
        crows = _get_persist_rows(self.view, True)
        if crows is not None:
            crows.clear()
            for r in drows:
                crows.append(r + 1)

        # Update visual signets, brutally. This is the ST way.
        regions = []
        for r in drows:
            pt = self.view.text_point(r, 0)  # 0-based
            regions.append(sublime.Region(pt, pt))

        settings = sublime.load_settings("SbotSignet.sublime-settings")
        self.view.add_regions(SIGNET_REGION_NAME, regions, settings.get('signet_scope'), SIGNET_ICON)


#-----------------------------------------------------------------------------------
class SbotGotoSignetCommand(sublime_plugin.TextCommand):
    ''' Navigate to next/prev signet in whole collection. '''

    def run(self, edit, where):
        next = where == 'next'
        ''' Common navigate to signet in whole collection. next if True else prev. '''

        view = self.view
        window = view.window()
        winid = window.id()

        if winid not in _sigs:
            return

        settings = sublime.load_settings("SbotSignet.sublime-settings")
        signet_nav_files = settings.get('signet_nav_files')

        done = False
        sel_row, _ = view.rowcol(view.sel()[0].a)  # current sel
        incr = +1 if next else -1
        array_end = 0 if next else -1

        # 1) next: If there's another bookmark below >>> goto it
        # 1) prev: If there's another bookmark above >>> goto it
        if not done:
            sig_rows = _get_display_signet_rows(view)
            if next:
                sig_rows.reverse()

            for sr in sig_rows:
                if (next and sr > sel_row) or (not next and sr < sel_row):
                    view.run_command("goto_line", {"line": sr + 1})
                    done = True
                    break

            # At begin or end. Check for single file operation.
            if not done and not signet_nav_files and len(sig_rows) > 0:
                view.run_command("goto_line", {"line": sig_rows[0] + 1})
                done = True

        # 2) next: Else if there's an open signet file to the right of this tab >>> focus tab, goto first signet
        # 2) prev: Else if there's an open signet file to the left of this tab >>> focus tab, goto last signet
        if not done:
            view_index = window.get_view_index(view)[1] + incr
            while not done and ((next and view_index < len(window.views()) or (not next and view_index >= 0))):
                vv = window.views()[view_index]
                sig_rows = _get_display_signet_rows(vv)
                if len(sig_rows) > 0:
                    window.focus_view(vv)
                    vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                    done = True
                else:
                    view_index += incr

        # 3) next: Else if there is a signet file in the project that is not open >>> open it, focus tab, goto first signet
        # 3) prev: Else if there is a signet file in the project that is not open >>> open it, focus tab, goto last signet
        if not done:
            winid = window.id()

            for fn, rows in _sigs[winid].items():
                if fn is not None:
                    if window.find_open_file(fn) is None and os.path.exists(fn) and len(rows) > 0:
                        vv = window.open_file(fn)
                        endrow = rows[array_end]
                        sublime.set_timeout(lambda r=endrow: _wait_load_file(vv, r), 10)  # already 1-based in file
                        window.focus_view(vv)
                        done = True
                        break

        # 4) next: Else >>> find first tab/file with signets, focus tab, goto first signet
        # 4) prev: Else >>> find last tab/file with signets, focus tab, goto last signet
        if not done:
            view_index = 0 if next else len(window.views()) - 1
            while not done and ((next and view_index < len(window.views()) or (not next and view_index >= 0))):
                vv = window.views()[view_index]
                sig_rows = _get_display_signet_rows(vv)
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
        global _sigs

        # Clear collection for current window only.
        winid = self.view.window().id()
        if winid in _sigs:
            _sigs[winid] = {}

        # Clear visuals in open views.
        for vv in self.view.window().views():
            vv.erase_regions(SIGNET_REGION_NAME)


#-----------------------------------------------------------------------------------
def _wait_load_file(view, line):
    ''' Open file asynchronously then position at line. '''
    if view.is_loading():
        sublime.set_timeout(lambda: _wait_load_file(view, line), 100)  # maybe not forever?
    else:  # good to go
        view.run_command("goto_line", {"line": line})


#-----------------------------------------------------------------------------------
def _get_display_signet_rows(view):
    ''' Get all the signet row numbers in the view. Returns a sorted list. '''

    sig_rows = []
    for reg in view.get_regions(SIGNET_REGION_NAME):
        row, _ = view.rowcol(reg.a)
        sig_rows.append(row)
    sig_rows.sort()
    return sig_rows


#-----------------------------------------------------------------------------------
def _get_persist_rows(view, init_empty):
    ''' General helper to get the data values from collection. If init_empty and there are none, add a default value. '''

    global _sigs

    vals = None  # Default
    winid = view.window().id()
    fn = view.file_name()

    if winid in _sigs:
        if fn not in _sigs[winid]:
            if init_empty:
                # Add a new one.
                _sigs[winid][fn] = []
                vals = _sigs[winid][fn]
        else:
            vals = _sigs[winid][fn]

    return vals
