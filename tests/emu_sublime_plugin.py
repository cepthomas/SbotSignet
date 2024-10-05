
# https://www.sublimetext.com/docs/api_reference.html

# If you are going to interact with the current view, use TextCommand,
# otherwise use WindowCommand. Unknown use for ApplicationCommand.
#
# EventListener Class: Note that many of these events are triggered by the buffer underlying the view,
# and thus the method is only called once, with the first view as the parameter.
#
# ViewEventListener Class: A class that provides similar event handling to EventListener, but bound
# to a specific view. Provides class method-based filtering to control what views objects are created for.

class CommandInputHandler():
    pass


class TextInputHandler(CommandInputHandler):
    pass


class ListInputHandler(CommandInputHandler):
    pass


class Command():
    pass


class WindowCommand(Command):
    def __init__(self, window):
        self.window = window


class TextCommand(Command):
    def __init__(self, view):
        self.view = view


class EventListener():
    pass


class ViewEventListener():
    def __init__(self, view):
        self.view = view


class ZipImporter:
    pass

