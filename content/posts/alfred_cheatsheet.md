---
title: "Alfred Cheatsheet"
date: "2026-06-14T00:00:00+08:00"
tags: ["mac", "alfred", "cheatsheet"]
description: "Concise Alfred shortcuts and examples"
---

## App Launcher

Trigger: `Option + Space` -> type app name.

| Shortcut / Input | Usage |
| --- | --- |
| `Option + Space` | Show Alfred |
| `<app name>` + `Return` | Open an app |
| `Command + 1` to `Command + 9` | Open result by number |
| `Command + ,` | Open Alfred Preferences |

Examples:

```text
chrome
terminal
vscode
activity monitor
```

## Default Search

Trigger: `Option + Space` -> type query without a keyword.

| Shortcut / Input | Usage |
| --- | --- |
| `<query>` | Search default results |
| `Return` | Open selected result |
| `Shift` or `Command + Y` | Quick Look preview |
| `Command + Return` | Reveal local file in Finder |
| `Option + Return` | Search query in Finder |
| `Control + Return` | Search query on web |
| `Escape` | Hide Alfred or go back |

Examples:

```text
docker
keyboard
network
```

## File Search

Trigger: `Option + Space` -> type a file-search keyword, then the query.

| Keyword / Shortcut | Usage |
| --- | --- |
| `open <query>` | Open a file |
| `find <query>` | Reveal a file in Finder |
| `in <query>` | Search inside files |
| `tags <query>` | Search by Finder tags |
| `Space` + `<query>` | Quick file search |
| `/` | Browse from root folder |
| `~` | Browse home folder |
| `Backspace` | Go up one folder |
| `Tab` | Autocomplete |

Examples:

```text
Option + Space -> open resume
Option + Space -> find nginx.conf
Option + Space -> in prometheus
Option + Space -> tags invoice
Option + Space -> Space -> Downloads
```

## File Actions

Trigger: search or select a file in Alfred -> press an action shortcut.

| Shortcut | Usage |
| --- | --- |
| `Right Arrow` | Show actions for selected result |
| `Command + /` | Show Universal Actions |
| `Option + Down` | Add file to buffer and move down |
| `Option + Up` | Add or remove file from buffer |
| `Option + Left` | Remove last file from buffer |
| `Option + Right` | Action all files in buffer |

Examples:

```text
Option + Space -> find nginx.conf -> Right Arrow -> Copy Path
Option + Space -> find report.pdf -> Right Arrow -> Move To
Option + Space -> find invoice -> Option + Down -> Option + Right -> Email
```

## Web Search

Trigger: `Option + Space` -> type web-search keyword, then query.

| Keyword | Usage |
| --- | --- |
| `google <query>` | Google search |
| `wiki <query>` | Wikipedia search |
| `amazon <query>` | Amazon search |
| Custom keyword | Search a configured website |

Examples:

```text
Option + Space -> google alfred workflows
Option + Space -> wiki tcp congestion control
Option + Space -> github prometheus promql
Option + Space -> so golang context timeout
```

## Calculator

Trigger: `Option + Space` -> type a math expression.

| Input | Usage |
| --- | --- |
| `<expression>` | Basic calculation |
| `=` | Advanced calculation mode, if enabled |
| `Return` | Copy result |

Examples:

```text
13*567
1024/8
20% of 349
=sqrt(144)
```

## Dictionary

Trigger: `Option + Space` -> type dictionary keyword, then word.

| Keyword | Usage |
| --- | --- |
| `define <word>` | Show definition |
| `spell <word>` | Show spelling suggestions |

Examples:

```text
define ephemeral
spell concensus
```

## Clipboard History

Powerpack feature.

Trigger: `Option + Command + C`.

| Shortcut / Keyword | Usage |
| --- | --- |
| `Option + Command + C` | Open Clipboard History |
| `<query>` | Search clipboard history |
| `Return` | Paste selected clip |
| `Command + C` | Copy selected clip |
| `clear` | Clear clipboard history |
| `Command + S` | Save selected clip as snippet |
| `Fn + Backspace` | Delete selected clip |

Examples:

```text
Open Clipboard History -> search "token" -> Return
Open Clipboard History -> search "http" -> Command + C
clear
```

## Snippets

Powerpack feature.

Trigger: type the snippet keyword in any app, or use `Option + Space` -> `snip`.

| Keyword / Input | Usage |
| --- | --- |
| `snip` | Browse snippets |
| `<snippet keyword>` | Expand snippet while typing |

Examples:

```text
;mail -> name@example.com
;sig  -> email signature
;zoom -> meeting link
;addr -> address
```

## System Commands

Trigger: `Option + Space` -> type system command keyword.

| Keyword | Usage |
| --- | --- |
| `lock` | Lock Mac |
| `sleep` | Sleep Mac |
| `sleepdisplays` | Sleep displays |
| `screensaver` | Start screen saver |
| `restart` | Restart Mac |
| `shutdown` | Shut down Mac |
| `logout` | Log out |
| `trash` | Show Trash |
| `emptytrash` | Empty Trash |
| `eject` | Eject removable media |
| `ejectall` | Eject all removable media |
| `hide` | Hide current app |
| `quit` | Quit current app |
| `quitall` | Quit all apps |
| `forcequit` | Force quit current app |
| `volup` | Increase volume |
| `voldown` | Decrease volume |
| `mute` | Toggle mute |

Examples:

```text
lock
sleepdisplays
emptytrash
quitall
```

## Terminal / Shell

Trigger: `Option + Space` -> type `>` followed by a shell command.

| Prefix | Usage |
| --- | --- |
| `>` | Run shell command in Terminal |

Examples:

```text
> pwd
> top
> brew update
```

## Contacts

Trigger: `Option + Space` -> type contact name or `email <name>`.

| Keyword / Input | Usage |
| --- | --- |
| `<contact name>` | Search contacts |
| `email <name>` | Compose email |
| `Return` on email field | Open email draft |

Examples:

```text
john
email john
```

## Music

Powerpack feature.

Trigger: `Control + Command + Return`, or `Option + Space` -> `music`.

| Shortcut / Keyword | Usage |
| --- | --- |
| `Control + Command + Return` | Show Music Mini Player |
| `music` | Show Music Mini Player |
| `Control + Command + Down` | Play / pause |
| `Control + Command + Right` | Next track |
| `Control + Command + Left` | Previous track |
| `Control + Command + Up` | Play random album |
| `play` / `pause` | Play or pause |
| `next` | Next track |
| `back` / `previous` | Previous track |
| `volmax` | Maximum volume |
| `volmid` | Half volume |
| `mute` | Mute |

Examples:

```text
music
next
random
```

## Workflows

Powerpack feature.

Trigger: `Option + Space` -> type the workflow keyword.

| Input | Usage |
| --- | --- |
| `<workflow keyword>` | Run workflow |
| `<workflow keyword> <argument>` | Run workflow with argument |
| Workflow hotkey | Run workflow directly |

Examples:

```text
uuid
timestamp 1718271000
gh prometheus
jira ABC-123
dash service-name
```

## Help

Trigger: `Option + Space` -> type `?` command.

| Input | Usage |
| --- | --- |
| `?hotkeys` | Search Alfred hotkeys |
| `?keywords` | Search Alfred keywords |
| `?<feature>` | Search help for a feature |

Examples:

```text
?hotkeys
?clipboard
?workflows
```

## Reference

- [Alfred official cheatsheet](https://www.alfredapp.com/help/getting-started/cheatsheet/)
- [Alfred features](https://www.alfredapp.com/help/features/)
- [Alfred workflows](https://www.alfredapp.com/help/workflows/)
