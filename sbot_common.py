import sys
import os
import pathlib
import enum
import sublime
import sublime_plugin


# Internal categories.
CAT_NON = '---'
CAT_INF = 'INF'
CAT_WRN = 'WRN'
CAT_ERR = 'ERR'
CAT_TRC = 'TRC'
CAT_DBG = 'DBG'
CAT_EXC = 'EXC'


#-----------------------------------------------------------------------------------
def slog(cat: str, message='???'):
    ''' Format a standard message with caller info and print it.
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

    print(f'{cat} {fn}:{line} {message}')

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
    # slog(CAT_DBG, f'|{project_fn}|{file_ext}|{fn}|{store_fn}')
    return store_fn


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
