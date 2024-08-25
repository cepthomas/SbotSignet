# SbotSignet

Enhanced bookmarks:
- `Bookmark` and `mark` are already taken so I use `signet` which means in French:
> "Petit ruban ou filet qu'on insère entre les feuillets d'un livre pour marquer l'endroit que l'on veut retrouver."
- Next/previous (optionally) traverses files in project - like VS.

Built for ST4 on Windows and Linux.

Persistence files are in `.../Packages/User/.SbotStore` as `*.sigs`.


## Commands
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

Or they could go in your `User\Main.sublime-menu` file.

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
because you shouldn't need both. In `User\Default (Windows).sublime-keymap` file (or Linux).

``` json
{ "keys": ["ctrl+f2"], "command": "sbot_toggle_signet" },
{ "keys": ["f2"], "command": "sbot_goto_signet", "args": { "where": "next" } },
{ "keys": ["shift+f2"], "command": "sbot_goto_signet", "args": { "where": "prev" } },
{ "keys": ["ctrl+shift+f2"], "command": "sbot_clear_signets" },
```


## Settings
| Setting              | Description                          | Options                                      |
| :--------            | :-------                             | :------                                      |
| scope                | Scope name for gutter icon color     |                                              |
| nav_files            | Traverse  extent                     | true=all files or false=just current file    |
