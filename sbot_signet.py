import sys
import os
import json
import sublime
import sublime_plugin
from . import sbot_common as sc


# TODO Allow signets for temp/scratch files. Not persisted until saved w/filename.


# Definitions.
SIGNET_REGION_NAME = 'signet_region'
SIGNET_ICON = 'Packages/Theme - Default/common/label.png'

# The current signets. This is global across all ST instances/window/projects.
_sigs = {}
# {
#     "my.sublime-project": {
#         "file_with_signets_1.ext": [100, 200, ...],
#         "file_with_signets_2.ext": [101, 201, ...],
#         ...
#     },
#     ...
# }



#-----------------------------------------------------------------------------------
def plugin_loaded():
    '''Called per plugin instance.'''
    pass


#-----------------------------------------------------------------------------------
class SignetEvent(sublime_plugin.EventListener):
    ''' Listener for view specific events of interest. '''

    # Need to track what's been initialized.
    _views_inited = set()

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Load the persistence file. Views are valid.
        Note that this also happens if this module is reloaded - like when editing this file. '''
        if len(views) > 0:
            view = views[0]
            win = view.window()
            if win is not None:
                project_fn = win.project_file_name()
                self._read_store()
                for view in views:
                    self._init_view(view)

    def on_load_project(self, window):
        ''' This gets called for new windows but not for the first one. '''
        for view in window.views():
            self._init_view(view)

    def on_pre_close_project(self, window):
        ''' Save to file when closing window/project. '''
        self._write_store()

    def on_load(self, view):
        ''' Load a new file. '''
        self._init_view(view)

    # def on_pre_close(self, view):
    #     ''' This happens after on_pre_close_project(). Get the current sigs for the view. '''
    #     self._collect_sigs(view)

    def on_deactivated(self, view):
        ''' This happens after view loses focus. Get the current sigs for the view. '''
        self._collect_sigs(view)

    def _init_view(self, view):
        ''' Lazy init. '''
        fn = view.file_name()
        if view.is_scratch() is True or fn is None:
            return

        project_sigs = _get_project_sigs(view, init=False)
        if project_sigs is None:
            return

        # Init the view if not already.
        vid = view.id()
        if vid not in self._views_inited:
            self._views_inited.add(vid)

            # Init the view with any persisted values.
            rows = None  # Default
            winid = view.window().id()
            fn = view.file_name()

            if fn in project_sigs:
                rows = project_sigs[fn]

            if rows is not None:
                # Update visual signets, brutally. This is the ST way.
                regions = []
                for r in rows:
                    pt = view.text_point(r - 1, 0)  # ST is 0-based
                    regions.append(sublime.Region(pt, pt))
                settings = sublime.load_settings(sc.get_settings_fn())
                view.add_regions(SIGNET_REGION_NAME, regions, settings.get('scope'), SIGNET_ICON)

    def _read_store(self):
        ''' General project opener. Cleans up bad entries '''
        global _sigs

        store_fn = sc.get_store_fn()
        if os.path.isfile(store_fn):
            try:
                with open(store_fn, 'r') as fp:
                    _temp_sigs = json.load(fp)
                    # Sanity checks. Easier to make a new clean collection rather than remove parts.
                    _sigs.clear()

                    for proj_fn, proj_sigs in _temp_sigs.items():
                        if os.path.exists(proj_fn):
                            files = {}
                            for fn, lines in _temp_sigs[proj_fn].items():
                                if os.path.exists(fn) and len(lines) > 0:
                                    files[fn] = lines
                            if len(files) > 0:
                                _sigs[proj_fn] = files

            except Exception as e:
                sc.error(f'Error reading {store_fn}: {e}', e.__traceback__)

        else:  # Assume new file with default fields.
            sublime.status_message('Creating new signets file')
            _sigs = {}

    def _write_store(self):  #, window):
        ''' Save everything. '''
        global _sigs

        store_fn = sc.get_store_fn()

        try:
            with open(store_fn, 'w') as fp:
                json.dump(_sigs, fp, indent=4)
        except Exception as e:
            sc.error(f'Error writing {store_fn}: {e}', e.__traceback__)

    def _collect_sigs(self, view):
        ''' Update the signets from the view as they may have moved during editing. '''

        fn = view.file_name()
        window = view.window()

        project_sigs = _get_project_sigs(view, init=False)

        if project_sigs is not None:
            regions = view.get_regions(SIGNET_REGION_NAME)

            if len(regions) > 0:
                if fn in project_sigs:
                    project_sigs[fn].clear()
                else:
                    project_sigs[fn] = []

                for reg in regions:
                    row, _ = view.rowcol(reg.a)
                    project_sigs[fn].append(row + 1)
            else:
                try:
                    project_sigs.delete(fn)
                except:
                    pass


#-----------------------------------------------------------------------------------
class SbotToggleSignetCommand(sublime_plugin.TextCommand):
    ''' Flip the signet. '''

    def is_visible(self):
        # Don't allow signets in temp views.
        return self.view.is_scratch() is False and self.view.file_name() is not None

    def run(self, edit):
        del edit

        view = self.view
        win = view.window()
        fn = view.file_name()

        # Don't allow signets in temp views.
        if view.is_scratch() is True or view.file_name() is None:
            return

        # Get current selected row.
        caret = sc.get_single_caret(view)
        if caret is None:
            return  # -- early return

        sel_row, _ = view.rowcol(caret)
        sig_rows = _get_view_signet_rows(view)

        if sel_row != -1:
            # Do the toggle. Is there one currently at the selected row?
            existing = sel_row in sig_rows
            if existing:
                sig_rows.remove(sel_row)
            else:
                sig_rows.append(sel_row)

        # Update collection.
        project_sigs = _get_project_sigs(view)

        if project_sigs is not None:
            project_sigs[fn] = sig_rows

            # Update visual signets, brutally. This is the ST way.
            regions = []
            for r in sig_rows:
                pt = view.text_point(r, 0)  # 0-based
                regions.append(sublime.Region(pt, pt))

            settings = sublime.load_settings(sc.get_settings_fn())
            view.add_regions(SIGNET_REGION_NAME, regions, str(settings.get('scope')), SIGNET_ICON)


#-----------------------------------------------------------------------------------
class SbotGotoSignetCommand(sublime_plugin.TextCommand):
    ''' Navigate to next/previous/select signet in whole collection. '''

    panel_items = []

    def run(self, edit, where):
        # Common navigate to signet in whole collection.
        del edit

        project_sigs = _get_project_sigs(self.view, init=False)
        if project_sigs is None:
            return  # --- early return

        view = self.view
        win = view.window()
        if win is None:
            return  # --- early return

        ### What kind of request?
        if where == 'sel': # user select specific signet
            self.panel_items.clear()

            for fn, lines in project_sigs.items():
                for line in lines:
                    self.panel_items.append(sublime.QuickPanelItem(trigger=f'{fn} line:{line}', kind=sublime.KIND_AMBIGUOUS))
            win = self.view.window()
            if win is not None:
                win.show_quick_panel(self.panel_items, on_select=self.on_sel_sig)

        else:
            caret = sc.get_single_caret(view)
            if caret is None:
                return  # -- early return

            next = where == 'next'

            settings = sublime.load_settings(sc.get_settings_fn())
            nav_all_files = settings.get('nav_all_files')

            sel_row, _ = view.rowcol(caret)  # current selected row
            incr = +1 if next else -1
            array_end = 0 if next else -1

            done = False

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
                if not done and not nav_all_files and len(sig_rows) > 0:
                    view.run_command("goto_line", {"line": sig_rows[0] + 1})
                    done = True

            # 2) next: Else if there's an open signet file to the right of this tab -> focus tab, goto first signet
            # 2) prev: Else if there's an open signet file to the left of this tab -> focus tab, goto last signet
            if not done:
                view_index = win.get_view_index(view)[1] + incr
                while not done and ((next and view_index < len(win.views()) or (not next and view_index >= 0))):
                    vv = win.views()[view_index]
                    sig_rows = _get_view_signet_rows(vv)
                    if len(sig_rows) > 0:
                        win.focus_view(vv)
                        vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                        done = True
                    else:
                        view_index += incr

            # 3) next: Else if there is a signet file in the project that is not open -> open it, focus tab, goto first signet
            # 3) prev: Else if there is a signet file in the project that is not open -> open it, focus tab, goto last signet
            if not done:
                for fn, rows in project_sigs.items():
                    if fn is not None:
                        if win.find_open_file(fn) is None and os.path.exists(fn) and len(rows) > 0:
                            vv = sc.wait_load_file(win, fn, rows[array_end])
                            done = True
                            break

            # 4) next: Else -> find first tab/file with signets, focus tab, goto first signet
            # 4) prev: Else -> find last tab/file with signets, focus tab, goto last signet
            if not done:
                view_index = 0 if next else len(win.views()) - 1
                while not done and ((next and view_index < len(win.views()) or (not next and view_index >= 0))):
                    vv = win.views()[view_index]
                    sig_rows = _get_view_signet_rows(vv)
                    if len(sig_rows) > 0:
                        win.focus_view(vv)
                        vv.run_command("goto_line", {"line": sig_rows[array_end] + 1})
                        done = True
                    else:
                        view_index += incr

    def on_sel_sig(self, *args, **kwargs):
        ''' User signet selection. '''
        del kwargs
        if len(args) > 0 and args[0] >= 0:
            fspec = self.panel_items[args[0]].trigger
            parts = fspec.split('line:')
            fn = parts[0].strip()
            line = int(parts[1].strip())

            # Open the file if not already.
            win = self.view.window()

            vv = win.find_open_file(fn)
            if vv is None:
                vv = sc.wait_load_file(win, fn, line)
            win.focus_view(vv)
            vv.run_command("goto_line", {"line": line})

    def is_visible(self):
        project_sigs = _get_project_sigs(self.view, init=False)
        return project_sigs is not None


#-----------------------------------------------------------------------------------
class SbotClearAllSignetsCommand(sublime_plugin.TextCommand):
    ''' Clear all signets in project. '''

    def run(self, edit):
        del edit

        project_sigs = _get_project_sigs(self.view, init=False)
        if project_sigs is None:
            return  # --- early return

        # Bam.
        try:
            del _sigs[self.view.window().project_file_name()]  # pyright: ignore
        # except Exception as e:
        #     pass
        finally:
            # Clear visuals in open views.
            win = self.view.window()
            if win is not None:
                for v in win.views():
                    v.erase_regions(SIGNET_REGION_NAME)


#-----------------------------------------------------------------------------------
class SbotClearFileSignetsCommand(sublime_plugin.TextCommand):
    ''' Clear signets in current file. '''

    def run(self, edit):
        del edit

        project_sigs = _get_project_sigs(self.view, init=False)
        if project_sigs is None:
            return  # --- early return

        # Bam.
        try:
            del _sigs[self.view.window().project_file_name()][self.view.file_name()]  # pyright: ignore
        # except Exception as e:
        #     pass
        finally:
            # Clear visuals in open views.
            win = self.view.window()
            if win is not None:
                for v in win.views():
                    v.erase_regions(SIGNET_REGION_NAME)


#-----------------------------------------------------------------------------------
def _get_view_signet_rows(view):
    ''' Get all the signet row numbers in the view. Returns a sorted list. '''
    sig_rows = []
    for reg in view.get_regions(SIGNET_REGION_NAME):
        row, _ = view.rowcol(reg.a)
        sig_rows.append(row)
    sig_rows.sort()
    return sig_rows


#-----------------------------------------------------------------------------------
def _get_project_sigs(view, init=True):
    ''' Get the signets associated with this view or None. Option to create a new entry if missing.'''
    sigs = None
    win = view.window()
    if win is not None:
        project_fn = win.project_file_name()
        if project_fn not in _sigs:
            if init:
                _sigs[project_fn] = {}
                sigs = _sigs[project_fn]
        else:
            sigs = _sigs[project_fn]
    return sigs