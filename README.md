# Signet Bookmarks

Sublime Text plugin for enhanced bookmarks. `Bookmark` and `Mark` are already well used so
this is `signet` from the French:
> "Petit ruban ou filet qu'on insère entre les feuillets d'un livre pour marquer l'endroit que l'on veut retrouver."

Built for ST4 on Windows and Linux (lightly tested).


## Features

- Persisted per project to `...\Packages\User\.SbotStore\<project>.sigs`.
- Next/previous traverses just the current file or all files in project.


## Commands and Menus

| Command                    | Description                   | Args             |
| :--------                  | :-------                      | :--------        |
| sbot_toggle_signet         | Toggle signet at row          |                  |
| sbot_goto_signet           | Goto next signet              | where: next      |
| sbot_goto_signet           | Goto previous signet          | where: prev      |
| sbot_clear_all_signets     | Clear all signets             |                  |


There is no default `Context.sublime-menu` file in this plugin.
Add the commands you like to your own `User\Context.sublime-menu` file. Typical entries are:
``` json
{ "caption": "Signet",
    "children":
    [
        { "caption": "Toggle Signet", "command": "sbot_toggle_signet" },
        { "caption": "Next Signet", "command": "sbot_goto_signet", "args": { "where": "next" } },
        { "caption": "Previous Signet", "command": "sbot_goto_signet", "args": { "where": "prev" } },
        { "caption": "Clear All Signets", "command": "sbot_clear_all_signets" }
    ]
}
```

Or they could go in your `User\Main.sublime-menu` file under `Goto`.

``` json
{
    "id": "goto",
    "children":
    [
        {
            "id": "signets",
            "caption": "Signets",
            "children":
            [
                { "caption": "Toggle Signet", "command": "sbot_toggle_signet" },
                { "caption": "Next Signet", "command": "sbot_goto_signet", "args": { "where": "next" } },
                { "caption": "Previous Signet", "command": "sbot_goto_signet", "args": { "where": "prev" } },
                { "caption": "Clear Signets", "command": "sbot_clear_signets" },
            ]
        },
    ]
}
```    

You may find it useful to replace the builtin bookmark key bindings with the new ones
because you shouldn't need both. In `User\Default (Windows or Linux).sublime-keymap` file:

``` json
{ "keys": ["ctrl+f2"], "command": "sbot_toggle_signet" },
{ "keys": ["f2"], "command": "sbot_goto_signet", "args": { "where": "next" } },
{ "keys": ["shift+f2"], "command": "sbot_goto_signet", "args": { "where": "prev" } },
{ "keys": ["ctrl+shift+f2"], "command": "sbot_clear_signets" },
```


## Settings
| Setting       | Description                 | Options                                              |
| :--------     | :-------                    | :------                                              |
| scope         | Scope name for gutter icon  |                                                      |
| nav_all_files | Traverse extent             | true=all project files OR false=just current file    |

## Notes

- `sbot_common.py` contains miscellaneous common components primarily for internal use by the sbot family.
  This includes a very simple logger primarily for user-facing information, syntax errors and the like.
  Log file is in $APPDATA\Sublime Text\Packages\User\.SbotStore\sbot.log.
