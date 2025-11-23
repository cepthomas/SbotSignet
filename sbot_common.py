import sys
import os
import traceback
import collections
import datetime
import pathlib
import shutil
import subprocess
import socket
import sublime
import sublime_plugin


# This will get replaced with a plugin specific name during the copy process.
_plugin_name = 'SBOT_DEV'

# Data type for shared scopes.
HighlightInfo = collections.namedtuple('HighlightInfo', 'scope_name, region_name, type')

# Track temporary view.
_temp_view_id = None

# Plugin data storage dir.
_store_path = os.path.join(sublime.packages_path(), 'User', _plugin_name)
pathlib.Path(_store_path).mkdir(parents=True, exist_ok=True)


#-----------------------------------------------------------------------------------
#---------------------------- Public uttility functions ----------------------------
#-----------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
def get_plugin_name():
    ''' How this is known internally.'''
    return _plugin_name


#-----------------------------------------------------------------------------------
def get_store_fn():
    ''' Where to keep this module's stuff.'''
    return os.path.join(_store_path, f'{_plugin_name}.store')


#-----------------------------------------------------------------------------------
def get_settings_fn():
    ''' Get the settings fn suitable for ST.'''
    return os.path.join(f'{_plugin_name}.sublime-settings')


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
    - path is fully expanded path or valid url or None if invalid.
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
            elif os.path.isfile(exp_path):
                dir, fn = os.path.split(exp_path)
            else:
                dir = None
                fn = None
        path = exp_path

    return (dir, fn, path)


#-----------------------------------------------------------------------------------
def open_path(path):
    '''Acts as if you had clicked the path in the UI. Honors your file associations.'''
    try:
        if sublime.platform() == 'osx':
            subprocess.call(['open', path])
        elif sublime.platform() == 'windows':
            os.startfile(path)
        else:  # linux variants
            subprocess.run(('xdg-open', path))
        return True
    except:
        return False


#-----------------------------------------------------------------------------------
def open_terminal(where):
    '''Open a terminal in where.'''

    if sublime.platform() == 'osx':
        os.system(f'open -a Terminal {where}')
    elif sublime.platform() == 'windows':
        subprocess.run(f'wt -d "{where}"', shell=False, check=False)  # W10+
    else:  # linux -- this works for gnome, other desktop types need a config item.
        subprocess.run(f'gnome-terminal --working-directory="{where}"', shell=False, check=False)
    # Kde -> konsole
    # xfce4 -> xfce4-terminal
    # Cinnamon -> x-terminal-emulator
    # MATE -> mate-terminal --window
    # Unity -> gnome-terminal --profile=Default


#-----------------------------------------------------------------------------------
#---------------------------- Logging functions ------------------------------------
#-----------------------------------------------------------------------------------

_log_fn = os.path.join(_store_path, f'{_plugin_name}.log')

# TCP configuration.
HOST = '127.0.0.1'
PORT = None # default = off  51111

# Optional ansi color (https://en.wikipedia.org/wiki/ANSI_escape_code)
USE_COLOR = True
ERROR_COLOR = 91 # br red  31 is reg red
DEBUG_COLOR = 93 # yellow
INFO_COLOR = None # 37/97 white

# Delimiter for socket message lines.
MDEL = '\n'

# NTerm // Parse the args: "127.0.0.1 59120"

#-----------------------------------------------------------------------------------
# Initialize logging. Maybe roll over log now.
if os.path.exists(_log_fn) and os.path.getsize(_log_fn) > 50000:
    bup = _log_fn.replace('.log', '_old.log')
    shutil.copyfile(_log_fn, bup)
    # Clear current log file.
    with open(_log_fn, 'w'):
        pass


#-----------------------------------------------------------------------------------
def error(message, tb=None):
    '''Client logger function.'''
    _write_log('ERR', message, tb)

    # Show the user some context info.
    info = [message]
    for s in traceback.format_tb(tb):
        if len(s) > 0:
            info.append(s[:-1])
    # info.append('See the log for details')
    sublime.error_message('\n'.join(info))  # This goes to console too.


#-----------------------------------------------------------------------------------
def info(message):
    '''Client logger function.'''
    _write_log('INF', message)
    sublime.status_message(message)


#-----------------------------------------------------------------------------------
def debug(message):
    '''Client logger function.'''
    _write_log('DBG', message)


#-----------------------------------------------------------------------------------
def _write_log(level, message, tb=None):
    '''Format a standard message with caller info and log it.'''

    # if _log_fn == INVALID_FN:
    #     raise RuntimeError('Logger has not been initialized.')

    # Sometimes get stray empty lines.
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

    time_str = f'{str(datetime.datetime.now())}'[0:-3]

    # Write the record. No need to be synchronized across multiple sbot plugins
    # as ST docs say that API runs on a single thread.
    with open(_log_fn, 'a') as log:
        out_line = f'{time_str} {level} {fn}:{line} {message}'
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
def write_remote(msg):
    # Create a TCP client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the server
        client_socket.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")

        # Color?
        color = None # default
        if USE_COLOR:
            if msg.startswith('ERR'): color = ERROR_COLOR
            elif msg.startswith('DBG'): color = DEBUG_COLOR
            elif msg.startswith('INF'): color = INFO_COLOR

        # Send it.
        msg = f'{msg}{MDEL}' if color is None else f'\033[{color}m{msg}\033[0m{MDEL}'
        client_socket.sendall(msg.encode('utf-8'))

    except ConnectionRefusedError:
        # print(f"Error: Connection refused. Is the server running on {HOST}:{PORT}?")
        pass

    except Exception as e:
        # print(f"An error occurred: {e}")
        pass

    finally:
        # Close the socket
        client_socket.close()
        # print("Connection closed.")
