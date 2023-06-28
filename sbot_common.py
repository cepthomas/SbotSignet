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


# Odds and ends shared by the plugin family.

# print(f'Loading {__file__}')


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
