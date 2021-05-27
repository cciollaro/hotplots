# Hotplots - Chia Plots Archiving Program
TODO: update to refrence hotplots
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
