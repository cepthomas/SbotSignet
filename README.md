# Signet Bookmarks

Sublime Text plugin for enhanced bookmarks. `Bookmark` and `Mark` are already well used so
this is `signet` from the French:
> "Petit ruban ou filet qu'on insère entre les feuillets d'un livre pour marquer l'endroit que l'on veut retrouver."

Built for ST4 on Windows. Linux and OSX should be ok but are minimally tested - PRs welcome.


## Features

- Persisted per project to `...\Packages\User\SignetBookmarks\SignetBookmarks.store`.
- Next/previous traverses just the current file or all files in project.

Caveats:
- Signets not supported in temp/unnamed views.


## Commands and Menus

| Command                    | Description                         | Args                       |
| :--------                  | :-------                            | :--------                  |
| sbot_toggle_signet         | Toggle signet at row                |                            |
| sbot_goto_signet           | Go to next/previous/select signet   | where: next OR prev OR sel |
| sbot_clear_all_signets     | Clear all signets in project        |                            |
| sbot_clear_file_signets    | Clear signets in current file       |                            |


There is no default `Context.sublime-menu` file in this plugin.
Add the commands you like to your own `User\Context.sublime-menu` file. Typical entries are:
``` json
{ "caption": "Signet",
    "children":
    [
        { "caption": "Toggle Signet", "command": "sbot_toggle_signet" },
        { "caption": "Next Signet", "command": "sbot_goto_signet", "args": { "where": "next" } },
        { "caption": "Previous Signet", "command": "sbot_goto_signet", "args": { "where": "prev" } },
        { "caption": "Select Signet", "command": "sbot_goto_signet", "args": { "where": "sel" } },
        { "caption": "Clear All", "command": "sbot_clear_all_signets" }
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
                { "caption": "Clear All", "command": "sbot_clear_all_signets" },
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
```


## Settings
| Setting       | Description                 | Options                                              |
| :--------     | :-------                    | :------                                              |
| scope         | Scope name for gutter icon  | any valid - default is region.redish                 |
| nav_all_files | Traverse extent             | true=all project files OR false=just current file    |

## Notes

- `sbot_common.py` contains miscellaneous common components primarily for internal use by the sbot family.
  This includes a very simple logger primarily for user-facing information, syntax errors and the like.
  Log file is in `<ST_PACKAGES_DIR>\User\SignetBookmarks\SignetBookmarks.log`.
- If you pull the source it must be in a directory named `Signet Bookmarks` rather than the repo name.
  This is to satisfy PackageControl naming requirements.
