# serial-monitor

## setup

[Poetry](https://python-poetry.org/docs/)が必要です．

Python 3.8 推奨です．

```
git clone https://github.com/Be4rR/serial-monitor.git
cd serial-monitor
poetry install
```

config.jsonに必要な設定を書き込みます．最低限`port`と`baudrate`が必要です．
```
{"port": "COM7", "baudrate": 115200, "plot_width": 300, "save_dir": "./data"}
```

実行します．
```
poetry run python script.py
```
