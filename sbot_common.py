import sys
import os
import traceback
import platform
import collections
import datetime
import pathlib
import shutil
import subprocess
import sublime
import sublime_plugin


#-----------------------------------------------------------------------------------
#---------------------------- Public types -----------------------------------------
#-----------------------------------------------------------------------------------

# Data type.
HighlightInfo = collections.namedtuple('HighlightInfo', 'scope_name, region_name, type')

LL_ERROR = 0
LL_INFO = 1
LL_DEBUG = 2


#-----------------------------------------------------------------------------------
#---------------------------- Private fields ---------------------------------------
#-----------------------------------------------------------------------------------

# Internal flag.
_temp_view_id = None

# Logger stuff.
_log_fn = None

# Debug or not.
_mode = int(os.environ.get('SBOT_MODE', 0))


#-----------------------------------------------------------------------------------
#---------------------------- Public functions -------------------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
def error(message, tb=None):
    '''Logger function.'''
    _write_log(LL_ERROR, message, tb)

    # Show the user some context info.
    info = [message]
    # if tb is not None:
    #     frame = traceback.extract_tb(tb)[-1]
    #     info.append(f'at {frame.name}({frame.lineno})')
    info.append('See the log for details')
    sublime.error_message('\n'.join(info))  # This goes to console too.


#-----------------------------------------------------------------------------------
def info(message):
    '''Logger function.'''
    _write_log(LL_INFO, message)
    sublime.status_message(message)


#-----------------------------------------------------------------------------------
def debug(message):
    '''Logger function.'''
    if _mode > 0:
        _write_log(LL_DEBUG, message)


#-----------------------------------------------------------------------------------
def get_store_fn(fn):
    '''Get store simple file name.'''
    store_path = os.path.join(sublime.packages_path(), 'User', '.SbotStore')
    pathlib.Path(store_path).mkdir(parents=True, exist_ok=True)
    store_fn = os.path.join(store_path, fn)
    return store_fn


#-----------------------------------------------------------------------------------
def get_single_caret(view):
    '''Get current caret position for one only region. If multiples, return None.'''
    if len(view.sel()) == 0:
        # raise RuntimeError('No data')
        return None
    elif len(view.sel()) == 1:  # single sel
        return view.sel()[0].b
    else:  # multi sel
        return None


#-----------------------------------------------------------------------------------
def get_sel_regions(view):
    '''Function to get user selection or the whole view if no selection.'''
    regions = []
    if len(view.sel()) > 0 and  len(view.sel()[0]) > 0:  # user sel
        regions = view.sel()
    else:
        regions = [sublime.Region(0, view.size())]
    return regions


#-----------------------------------------------------------------------------------
def create_new_view(window, text, reuse=True):
    '''Creates or reuse existing temp view with text. Returns the view.'''
    view = None
    global _temp_view_id

    # Locate the current temp view. This will silently fail if there isn't one.
    if reuse:
        for v in window.views():
            if v.id() == _temp_view_id:
                view = v
                break

    if view is None:
        # New instance.
        view = window.new_file()
        view.set_scratch(True)
        _temp_view_id = view.id()

    # Create/populate the view.
    view.run_command('select_all')
    view.run_command('cut')
    view.run_command('append', {'characters': text})  # insert has some odd behavior - indentation
    
    window.focus_view(view)

    return view


#-----------------------------------------------------------------------------------
def wait_load_file(window, fpath, line):
    '''Open file asynchronously then position at line. Returns the new View or None if failed.'''
    vnew = None

    def _load(view):
        if view.is_loading():
            sublime.set_timeout(lambda: _load(view), 10)  # maybe not forever?
        else:
            view.run_command("goto_line", {"line": line})

    # Open the file in a new view.
    try:
        vnew = window.open_file(fpath)
        _load(vnew)
    except Exception as e:
        error(f'Failed to open {fpath}: {e}', e.__traceback__)
        vnew = None

    return vnew


#-----------------------------------------------------------------------------------
def get_highlight_info(which='all'):
    '''Get list of builtin scope names and corresponding region names as list of HighlightInfo.'''
    hl_info = []
    if which == 'all' or which == 'user':
        for i in range(6):  # magic number of markup.user_hl* count.
            hl_info.append(HighlightInfo(f'markup.user_hl{i + 1}', f'region_user_hl{i + 1}', 'user'))
    if which == 'all' or which == 'fixed':
        for i in range(3):  # magic number of markup.fixed_hl* count.
            hl_info.append(HighlightInfo(f'markup.fixed_hl{i + 1}', f'region_fixed_hl{i + 1}', 'fixed'))
    return hl_info


#-----------------------------------------------------------------------------------
def expand_vars(s):
    '''Smarter version of builtin. Returns expanded string or None if bad var name.'''
    done = False
    count = 0
    while not done:
        if s is not None and '$' in s:
            sexp = os.path.expandvars(s)
            if s == sexp:
                # Invalid var.
                s = None
                done = True
            else:
                # Go around again.
                s = sexp
        else:
            # Done expanding.
            done = True

        # limit iterations
        if not done:
            count += 1
            if count >= 3:
                done = True
                s = None
    return s


#-----------------------------------------------------------------------------------
def get_path_parts(window, paths):
    '''
    Slide and dice into useful parts. paths is a list of which only the first is considered.
    Returns (dir, fn, path) where:
    - path is fully expanded path or None if invalid.
    - fn is None for a directory.
    '''
    dir = None
    fn = None
    path = None

    view = window.active_view()

    if paths is not None and len(paths) > 0:  # came from sidebar
        # Get the first element of paths.
        path = paths[0]
    elif view is not None:  # came from view menu
        # Get the view file.
        path = view.file_name()
    else:  # maybe image preview - dig out file name
        path = window.extract_variables().get('file')

    if path is not None:
        exp_path = expand_vars(path)
        if exp_path is not None:
            if os.path.isdir(exp_path):
                dir = exp_path
                path = exp_path
            elif os.path.isfile(exp_path):
                path = exp_path
                dir, fn = os.path.split(exp_path)
            else:
                dir = None
                fn = None
                path = None

    return (dir, fn, path)


#-----------------------------------------------------------------------------------
def open_path(path):
    '''Acts as if you had clicked the path in the UI. Honors your file associations.'''
    if platform.system() == 'Darwin':
        error('Sorry, we don\'t do Macs')
    elif platform.system() == 'Windows':
        os.startfile(path)
    else:  # linux variants
        subprocess.run(('xdg-open', path))
    return True
    

#-----------------------------------------------------------------------------------
def open_terminal(where):
    '''Open a terminal in where.'''

    # This works for gnome. Maybe should support other desktop types?
    # Kde -> konsole
    # xfce4 -> xfce4-terminal
    # Cinnamon -> x-terminal-emulator
    # MATE -> mate-terminal --window
    # Unity -> gnome-terminal --profile=Default

    if platform.system() == 'Darwin':
        error('Sorry, we don\'t do Macs')
    elif platform.system() == 'Windows':
        subprocess.run(f'wt -d "{where}"', shell=False, check=False)  # W10+
    else:  # linux
        subprocess.run(f'gnome-terminal --working-directory="{where}"', shell=False, check=False)


#-----------------------------------------------------------------------------------
#---------------------------- Private functions ------------------------------------
#-----------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------
def _write_log(level, message, tb=None):
    '''Format a standard message with caller info and log it.'''

    if _log_fn is None:
        raise RuntimeError('Logger has not been initialized.')

    # Gates. Sometimes get stray empty lines.
    if len(message) == 0:
        return
    if len(message) == 1 and message[0] == '\n':
        return

    # Get caller info.
    frame = sys._getframe(2)
    fn = os.path.basename(frame.f_code.co_filename)
    line = frame.f_lineno
    # f'func = {frame.f_code.co_name}'
    # f'mod_name = {frame.f_globals["__name__"]}'
    # f'class_name = {frame.f_locals["self"].__class__.__name__}'

    slvl = '???'
    if level == LL_ERROR: slvl = 'ERR'
    elif level == LL_INFO: slvl = 'INF'
    elif level == LL_DEBUG: slvl = 'DBG'

    time_str = f'{str(datetime.datetime.now())}'[0:-3]

    # Write the record. No need to be synchronized across multiple sbot plugins
    # as ST docs say that API runs on a single thread.
    with open(_log_fn, 'a') as log:
        out_line = f'{time_str} {slvl} {fn}:{line} {message}'
        log.write(out_line + '\n')
        if tb is not None:
            # The traceback formatter is a bit ugly - clean it up.
            tblines = []
            for s in traceback.format_tb(tb):
                if len(s) > 0:
                    tblines.append(s[:-1])
            stb = '\n'.join(tblines)
            log.write(stb + '\n')
        log.flush()


#-----------------------------------------------------------------------------------
#----------------------- Finish initialization -------------------------------------
#-----------------------------------------------------------------------------------

# Initialize logging.
_log_fn = get_store_fn('sbot.log')
# Maybe roll over log now.
if os.path.exists(_log_fn) and os.path.getsize(_log_fn) > 50000:
    bup = _log_fn.replace('.log', '_old.log')
    shutil.copyfile(_log_fn, bup)
    # Clear current log file.
    with open(_log_fn, 'w'):
        pass
