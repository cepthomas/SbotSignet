# What It Is

Enhanced bookmarks:

- `Bookmark` and `mark` are already taken so I use `signet` which means in French:
> "Petit ruban ou filet qu'on insère entre les feuillets d'un livre pour marquer l'endroit que l'on veut retrouver."
- Persists per document to sbot-sigs file.
- Next/previous (optionally) traverses files in project - like VS.
- Builtin bookmark key mappings have been stolen:
    - `ctrl+f2`: sbot_toggle_signet
    - `f2`: sbot_goto_signet - next
    - `shift+f2`: sbot_goto_signet - prev
    - `ctrl+shift+f2`: sbot_clear_signets

Built for ST4 on Windows and Linux.

Persistence file is in `%data_dir%\Packages\User\.SbotStore`.


## Commands
| Command                    | Implementation | Description                   | Args             |
| :--------                  | :-------       | :-------                      | :--------        |
| sbot_toggle_signet         | Context, Main  | Toggle signet at row          |                  |
| sbot_goto_signet           | Context, Main  | Goto next signet              | where = next     |
| sbot_goto_signet           | Context, Main  | Goto previous signet          | where = prev     |
| sbot_clear_all_signets     | Context, Main  | Clear all signets             |                  |

## Settings
| Setting              | Description                          | Options                                                  |
| :--------            | :-------                             | :------                                                  |
| scope                | Scope name for gutter icon color     |                                                          |
| nav_files            | Traverse  extent                     | true = all files OR false = just current file            |
