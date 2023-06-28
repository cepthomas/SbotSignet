import sys
import os
import pathlib
import shutil
import platform
import subprocess
import collections
import enum
import sublime
import sublime_plugin


print(f'>>>>>>> Loading {__file__}')


# Internal categories.
CAT_NON = '---'
CAT_ERR = 'ERR'
CAT_WRN = 'WRN'
CAT_INF = 'INF'
CAT_DBG = 'DBG'
CAT_TRC = 'TRC'

ALL_CATS = [CAT_NON, CAT_ERR, CAT_WRN, CAT_INF, CAT_DBG, CAT_TRC]

# This is shared across plugins.
HighlightInfo = collections.namedtuple('HighlightInfo', 'scope_name, region_name, type')


#-----------------------------------------------------------------------------------
def slog(cat: str, message='???'):
    '''
    Format a standard message with caller info and print it.
    Prints to sbot_logger if it is installed, otherwise goes to stdout aka ST console.
    Note that cat should be three chars or less.
    '''

    # Check user cat len.
    cat = (cat + CAT_NON)[:3]

    # Get caller info.
    frame = sys._getframe(1)
    fn = os.path.basename(frame.f_code.co_filename)
    line = frame.f_lineno
    # func = frame.f_code.co_name
    # mod_name = frame.f_globals["__name__"]
    # class_name = frame.f_locals['self'].__class__.__name__
    # full_func = f'{class_name}.{func}'

    msg = f'{cat} {fn}:{line} {message}'
    print(msg)


#-----------------------------------------------------------------------------------
def get_store_fn(fn):
    ''' General utility to get store simple file name. '''
    store_path = os.path.join(sublime.packages_path(), 'User', '.SbotStore')
    pathlib.Path(store_path).mkdir(parents=True, exist_ok=True)
    store_fn = os.path.join(store_path, fn)
    return store_fn


#-----------------------------------------------------------------------------------
def get_store_fn_for_project(project_fn, file_ext):
    ''' General utility to get store file name based on ST project name. '''
    fn = os.path.basename(project_fn).replace('.sublime-project', file_ext)
    store_fn = get_store_fn(fn)
    return store_fn


#-----------------------------------------------------------------------------------
def get_single_caret(view):
    ''' Get current caret position for one only region. If multiples, return None. '''
    if len(view.sel()) == 0:
        raise RuntimeError('valid??')
    elif len(view.sel()) == 1:  # single sel
        return view.sel()[0].b
    else:  # multi sel
        return None


#-----------------------------------------------------------------------------------
def get_sel_regions(view, settings):
    ''' Function to get selections or optionally the whole view if sel_all is True.'''
    regions = []
    if len(view.sel()[0]) > 0:  # user sel
        regions = view.sel()
    else:
        if settings.get('sel_all'):
            regions = [sublime.Region(0, view.size())]
    return regions


#-----------------------------------------------------------------------------------
def create_new_view(window, text):
    ''' Creates a temp view with text. Returns the view.'''
    vnew = window.new_file()
    vnew.set_scratch(True)
    vnew.run_command('append', {'characters': text})  # insert has some odd behavior - indentation
    return vnew


#-----------------------------------------------------------------------------------
def wait_load_file(window, fpath, line):
    ''' Open file asynchronously then position at line. Returns the new View or None if failed. '''
    vnew = None

    def _load(view):
        if vnew.is_loading():
            sublime.set_timeout(lambda: _load(vnew), 10)  # maybe not forever?
        else:
            vnew.run_command("goto_line", {"line": line})

    # Open the file in a new view.
    try:
        vnew = window.open_file(fpath)
        _load(vnew)
    except Exception as e:
        slog(CAT_ERR, f'Failed to open {fpath}: {e}')
        vnew = None

    return vnew


# #-----------------------------------------------------------------------------------
# def start_file(filepath):
#     ''' Like you double-clicked it. '''
#     ret = 0
#     try:
#         if platform.system() == 'Darwin':       # macOS
#             ret = subprocess.call(('open', filepath))
#         elif platform.system() == 'Windows':    # Windows
#             os.startfile(filepath)
#         else:                                   # linux variants
#             re = subprocess.call(('xdg-open', filepath))
#     except Exception as e:
#         slog(CAT_ERR, f'{e}')
#         ret = 90

#     return ret


# #-----------------------------------------------------------------------------------
# def run_script(filepath, window):
#     ''' Script runner. Currently only python. Creates a new view with output. '''
#     ret = 0
#     try:
#         cmd = ''
#         if filepath.endswith('.py'):
#             cmd = f'python "{filepath}"'

#         data = subprocess.run(cmd, capture_output=True, text=True)
#         output = data.stdout
#         errors = data.stderr
#         if len(errors) > 0:
#             output = output + '============ stderr =============\n' + errors
#         create_new_view(window, output)

#     except Exception as e:
#         slog(CAT_ERR, f'{e}')
#         ret = 91

#     return ret


#-----------------------------------------------------------------------------------
def get_highlight_info(which='all'):
    ''' Get list of builtin scope names and corresponding region names as list of HighlightInfo. '''
    hl_info = []
    if which == 'all' or which == 'user':
        for i in range(6):  # magical knowledge
            hl_info.append(HighlightInfo(f'markup.user_hl{i + 1}', f'region_user_hl{i + 1}', 'user'))
    if which == 'all' or which == 'fixed':
        for i in range(3):  # magical knowledge
            hl_info.append(HighlightInfo(f'markup.fixed_hl{i + 1}', f'region_fixed_hl{i + 1}', 'fixed'))
    return hl_info



#-----------------------------------------------------------------------------------
# def exec_file(filepath): # replace sbot_common.run_script() and sbot_common.start_file()
#     ''' Like you double-clicked it. or.... '''
#     ''' Script runner. Currently only python. Creates a new view with output. '''

#     its_a_script = False

#     ret = 0
    
#     try:
#         if its_a_script:
#             # sbot_common.run_script()
#             cmd = ''
#             if filepath.endswith('.py'):
#                 cmd = f'python "{filepath}"'

#             data = subprocess.run(cmd, capture_output=True, text=True)
#             output = data.stdout
#             errors = data.stderr
#             if len(errors) > 0:
#                 output = output + '============ stderr =============\n' + errors
#             create_new_view(window, output)

#         else: # plain click click
#             # sbot_common.start_file()
#             if platform.system() == 'Darwin':
#                 ret = subprocess.call(('open', filepath))
#             elif platform.system() == 'Windows':
#                 os.startfile(filepath)
#             else:  # linux variants
#                 re = subprocess.call(('xdg-open', filepath))
#     except Exception as e:
#         slog(CAT_ERR, f'{e}')
#         ret = 90

#     return ret


# def _get_dir(paths):
#     path = paths[0] if os.path.isdir(paths[0]) else os.path.split(paths[0])[0]
#     return path

# def _get_dir(view, paths):
#     ''' Get the directory name containing the specified path. '''

#     dirname = None

#     if paths is None:
#         # Get the view file.
#         fn = view.file_name()
#         if fn is not None:
#             dirname = os.path.dirname(fn)
#     elif len(paths) > 0:
#         # Get the first element of paths - from sidebar.
#         fn = paths[0]
#         dirname = os.path.dirname(fn)

#     return dirname

# def _get_file(view, paths):
#     ''' Get the selected file path. '''

#     filename = None

#     if paths is None:
#         # Get the view file.
#         filename = view.file_name()
#     elif len(paths) > 0:
#         # Get the first element of paths - from sidebar.
#         filename = paths[0]

#     return filename


def _get_path(view, paths):
    ''' Returns (dir, fn, path). fn is None for a directory. '''

    dir = None
    fn = None

    path = None

    if paths is None:
        # Get the view file.
        path = view.file_name()
    elif len(paths) > 0:
        # Get the first element of paths - from sidebar.
        path = paths[0]

    if path is not None:
        if os.path.isdir(path):
            dir = path
        else:
            ps = os.path.split(path)
            dir = ps[0]
            fn = ps[1]

    return (dir, fn, path)



#-----------------------------------------------------------------------------------
class SbotExecCommand(sublime_plugin.WindowCommand): 
    # like SbotSidebarRunScriptCommand, SbotUtilsRunScriptCommand, SbotUtilsExecCommand, SbotSidebarExecCommand,
    # sbot_common.run_script(), sbot_common.start_file()
    '''
    Simple executioner for exes/cmds without args, like you double clicked it.
    Assumes file associations are set to preferences.
    Supports context and sidebar menus. '''
    ''' Like you double-clicked it. or.... '''
    ''' Script runner. Currently only python. Creates a new view with output. '''

    def run(self, paths=None):
        dir, fn, path = _get_path(self.window.active_view(), paths)

        try:
            # Determine if it is a supported script type.
            ext = os.path.splitext(fn)[1]
            if ext in ['.py']: # list of known script types/execute patterns
                cmd = '???'
                if ext == '.py':
                    cmd = f'python "{path}"'
                data = subprocess.run(cmd, capture_output=True, text=True)
                output = data.stdout
                errors = data.stderr
                if len(errors) > 0:
                    output = output + '============ stderr =============\n' + errors
                create_new_view(self.window, output)
            else:
                if platform.system() == 'Darwin':
                    ret = subprocess.call(('open', path))
                elif platform.system() == 'Windows':
                    os.startfile(path)
                else:  # linux variants
                    re = subprocess.call(('xdg-open', path))
        except Exception as e:
            slog(CAT_ERR, f'{e}')

    def is_visible(self, paths=None):
        # Ensure file only.
        dir, fn, path = _get_path(self.window.active_view(), paths)
        return fn is not None


#-----------------------------------------------------------------------------------
class SbotTerminalCommand(sublime_plugin.WindowCommand):
    ''' Open term in this directory. Supports context and sidebar menus. '''
    # SbotUtilsTerminalCommand(sublime_plugin.WindowCommand), SbotSidebarTerminalCommand(sublime_plugin.WindowCommand):

    def run(self, paths=None):
        dir, fn, path = _get_path(self.window.active_view(), paths)

        cmd = '???'
        if platform.system() == 'Windows':
            ver = float(platform.win32_ver()[0])
            # slog(CAT_INF, ver)
            cmd = f'wt -d "{dir}"' if ver >= 10 else f'cmd /K "cd {dir}"'
        else: # mac/linux
            cmd = f'gnome-terminal --working-directory="{dir}"'
        subprocess.run(cmd, shell=False, check=False)


#-----------------------------------------------------------------------------------
class SbotCopyNameCommand(sublime_plugin.WindowCommand):
    ''' Get file or directory name to clipboard. Supports context and sidebar menus. '''

    def run(self, paths=None):
        dir, fn, path = _get_path(self.window.active_view(), paths)
        sublime.set_clipboard(os.path.split(path)[-1])

#-----------------------------------------------------------------------------------
class SbotCopyPathCommand(sublime_plugin.WindowCommand):
    ''' Get file or directory path to clipboard. Supports context and sidebar menus. '''

    def run(self, paths=None):
        dir, fn, path = _get_path(self.window.active_view(), paths)
        sublime.set_clipboard(path)

#-----------------------------------------------------------------------------------
class SbotCopyFileCommand(sublime_plugin.WindowCommand):
    ''' Copy selected file to the same dir. Supports context and sidebar menus. '''

    def run(self, paths=None):
        dir, fn, path = _get_path(self.window.active_view(), paths)

        # Find a valid file name.
        ok = False
        root, ext = os.path.splitext(path)
        for i in range(1, 9):
            newfn = f'{root}_{i}{ext}'
            if not os.path.isfile(newfn):
                shutil.copyfile(path, newfn)
                ok = True
                break

        if not ok:
            sublime.status_message("Couldn't copy file")

    def is_visible(self, paths=None):
        # Ensure file only.
        dir, fn, path = _get_path(self.window.active_view(), paths)
        return fn is not None
