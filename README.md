# Hotplots - Chia Plots Archiving Program
## Installation

_For updating from previous version, see section below._

1. Clone the repository

```
git clone https://github.com/cciollaro/hotplots.git
cd hotplots
```

2. Run the install script.

```
./install.sh
```

3. Copy the example config file

```
cp config-example.yaml config.yaml
```

4. Open up `config.yaml` in your editor and configure it to your preferences.

## Updating to the latest release

_Skip this if you followed the above section_.

```
cd hotplots

git fetch
git checkout main
git pull

./install.sh
```

> Important: Automated migration of config is not supported. Please check that your `config.yaml` has all new fields introduced in `config-example.yaml` and add anything missing. If correctly migrated, you shouldn't get any ERROR logs.

## Running in the background
You can use `tmux` (or `screen` if that's your preference, although I don't cover that here) to run hotplots in the background. 
The way I do this is via `tmux new -s hotplots` and then run `./start.sh` from inside the virtual terminal. You can detach with `Ctrl+b d`. 
You can view active tmux sessions with `tmux ls` and lastly you can re-attach with `tmux a -t hotplots`.

## Viewing active file transfers
The recommended method for viewing active is the `progress` command: https://github.com/Xfennec/progress.

This works both on the source (plotting) machine and the destination (harvesting) machine.

```
progress -w
```