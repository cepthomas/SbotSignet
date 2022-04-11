# What It Is
Enhanced bookmarks:

- `Bookmark` and `mark` are already taken so I shall use `signet` which means in French:
> "Petit ruban ou filet qu'on insère entre les feuillets d'un livre pour marquer l'endroit que l'on veut retrouver."
- Persists per document to sbot-sigs file.
- Next/previous (optionally) traverses files in project - like VS.
- Builtin bookmark key mappings have been stolen:
    - `ctrl+f2`: sbot_toggle_signet
    - `f2`: sbot_next_signet
    - `shift+f2`: sbot_previous_signet
    - `ctrl+shift+f2`: sbot_clear_signets

Built for ST4 on Windows and Linux.

## Commands
| Command                    | Implementation | Description                   | Args        |
| :--------                  | :-------       | :-------                      | :--------   |
| `sbot_toggle_signet`       | Context, Main  | Toggle signet at row          |             |
| `sbot_next_signet`         | Context, Main  | Goto next signet              |             |
| `sbot_previous_signet`     | Context, Main  | Goto previous signet          |             |
| `sbot_clear_all_signets`   | Context, Main  | Clear all signets             |             |

## Settings
| Setting              | Description                      | Options   |
| :--------            | :-------                         | :------   |
| `signet_scope`       | Scope name for gutter icon color |           |
| `signet_nav_files`   | Traverse  extent                 | `true` = all files OR `false` = just current file  |
