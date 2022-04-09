import os
import json
import pathlib
import sublime
import sublime_plugin

# TODO clear all sigs in project.

# Definitions.
SIGNET_REGION_NAME = 'signet'
SIGNET_ICON = 'Packages/Theme - Default/common/label.png'
SIGNET_FILE_EXT = '.sbot-sigs'
NEXT_SIG = 1
PREV_SIG = 2

# The current signet collections. Key is window id which corresponds to a project.
_sigs = None

# Need to track what's been initialized.
_views_inited = set()

# Where we keep the persistence.
_store_path = None


#-----------------------------------------------------------------------------------
class SignetEvent(sublime_plugin.EventListener):
    ''' Listener for view specific events of interest. See lifecycle notes in README.md. '''

    def on_init(self, views):
        ''' First thing that happens. '''
        global _store_path

        # Init now so signets are honored when no real views.
        _store_path = os.path.join(sublime.packages_path(), 'User', 'SbotStore')
        pathlib.Path(_store_path).mkdir(parents=True, exist_ok=True)
        
        view = views[0]
        _open_sigs(view.window().id(), view.window().project_file_name())


    def on_load(self, view):
        ''' Load an existing file. '''
        global _views_inited

        fn = view.file_name

        # Ignore transient views.
        if view.is_scratch() is False and fn is not None:
            vid = view.id()
            winid = view.window().id()

            # Init the view, maybe.
            if vid not in _views_inited:
                _views_inited.add(vid)

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

    def on_deactivated(self, view):
        ''' Save to file when focus/tab lost. '''
        if _sigs is not None:
            winid = view.window().id()
            if winid in _sigs:
                _save_sigs(winid, view.window().project_file_name())


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
class SbotNextSignetCommand(sublime_plugin.TextCommand):
    ''' Navigate to next signet in whole collection. '''

    def run(self, edit):
        _go_to_signet(self.view, NEXT_SIG)


#-----------------------------------------------------------------------------------
class SbotPreviousSignetCommand(sublime_plugin.TextCommand):
    ''' Navigate to previous signet in whole collection. '''

    def run(self, edit):
        _go_to_signet(self.view, PREV_SIG)


#-----------------------------------------------------------------------------------
class SbotClearSignetsCommand(sublime_plugin.TextCommand):
    ''' Clear all signets. '''

    def run(self, edit):
        # Remove from collection.
        rows = _get_persist_rows(self.view, False)
        if rows is not None:
            rows.clear()

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
def _get_store_fn(project_fn):
    ''' General utility. '''
    global _store_path
    project_fn = os.path.basename(project_fn).replace('.sublime-project', SIGNET_FILE_EXT)
    store_fn = os.path.join(_store_path, project_fn)
    return store_fn


#-----------------------------------------------------------------------------------
def _save_sigs(winid, project_fn):
    ''' General project saver. '''

    if project_fn is not None:
        store_fn = _get_store_fn(project_fn)

        # Remove invalid files and any empty values.
        if winid in _sigs.copy():
            # Safe iteration - accumulate elements to del later.
            del_els = []

            for fn, _ in _sigs[winid].items():
                if fn is not None:
                    if not os.path.exists(fn):
                        del_els.append((winid, fn))
                    elif len(_sigs[winid][fn]) == 0:
                        del_els.append((winid, fn))

            # Now remove from collection.
            for (w, fn) in del_els:
                del _sigs[w][fn]

            # Now save, or delete if empty.
            if len(_sigs[winid]) > 0:
                with open(store_fn, 'w') as fp:
                    json.dump(_sigs[winid], fp, indent=4)
            elif os.path.isfile(store_fn):
                os.remove(store_fn)


#-----------------------------------------------------------------------------------
def _open_sigs(winid, project_fn):
    ''' General project opener. '''

    global _sigs
    _sigs = {}

    if project_fn is not None:
        store_fn = _get_store_fn(project_fn)

        if os.path.isfile(store_fn):
            with open(store_fn, 'r') as fp:
                values = json.load(fp)
                _sigs[winid] = values
        else:
            # Assumes new file.
            sublime.status_message('Creating new signets file')
            _sigs[winid] = {}


#-----------------------------------------------------------------------------------
def _go_to_signet(view, direction):
    ''' Common navigate to signet in whole collection. direction is NEXT_SIG or PREV_SIG. '''

    if _sigs is None:
        return

    window = view.window()

    settings = sublime.load_settings("SbotSignet.sublime-settings")
    signet_nav_files = settings.get('signet_nav_files')

    done = False
    sel_row, _ = view.rowcol(view.sel()[0].a)  # current sel
    incr = +1 if direction == NEXT_SIG else -1
    array_end = 0 if direction == NEXT_SIG else -1

    # 1) NEXT_SIG: If there's another bookmark below >>> goto it
    # 1) PREV_SIG: If there's another bookmark above >>> goto it
    if not done:
        sig_rows = _get_display_signet_rows(view)
        if direction == PREV_SIG:
            sig_rows.reverse()

        for sr in sig_rows:
            if (direction == NEXT_SIG and sr > sel_row) or (direction == PREV_SIG and sr < sel_row):
                view.run_command("goto_line", {"line": sr + 1})
                done = True
                break

        # At begin or end. Check for single file operation.
        if not done and not signet_nav_files and len(sig_rows) > 0:
            view.run_command("goto_line", {"line": sig_rows[0] + 1})
            done = True

    # 2) NEXT_SIG: Else if there's an open signet file to the right of this tab >>> focus tab, goto first signet
    # 2) PREV_SIG: Else if there's an open signet file to the left of this tab >>> focus tab, goto last signet
    if not done:
        view_index = window.get_view_index(view)[1] + incr
        while not done and ((direction == NEXT_SIG and view_index < len(window.views()) or (direction == PREV_SIG and view_index >= 0))):
            vv = window.views()[view_index]
            sig_rows = _get_display_signet_rows(vv)
            if len(sig_rows) > 0:
                window.focus_view(vv)
                vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                done = True
            else:
                view_index += incr

    # 3) NEXT_SIG: Else if there is a signet file in the project that is not open >>> open it, focus tab, goto first signet
    # 3) PREV_SIG: Else if there is a signet file in the project that is not open >>> open it, focus tab, goto last signet
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

    # 4) NEXT_SIG: Else >>> find first tab/file with signets, focus tab, goto first signet
    # 4) PREV_SIG: Else >>> find last tab/file with signets, focus tab, goto last signet
    if not done:
        view_index = 0 if direction == NEXT_SIG else len(window.views()) - 1
        while not done and ((direction == NEXT_SIG and view_index < len(window.views()) or (direction == PREV_SIG and view_index >= 0))):
            vv = window.views()[view_index]
            sig_rows = _get_display_signet_rows(vv)
            if len(sig_rows) > 0:
                window.focus_view(vv)
                vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                done = True
            else:
                view_index += incr


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

    if _sigs is not None:
        if winid in _sigs:
            if fn not in _sigs[winid]:
                if init_empty:
                    # Add a new one.
                    _sigs[winid][fn] = []
                    vals = _sigs[winid][fn]
            else:
                vals = _sigs[winid][fn]

    return vals
