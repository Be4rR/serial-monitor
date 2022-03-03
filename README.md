# serial-monitor

## setup

[Git](https://git-scm.com/)と[Poetry](https://python-poetry.org/docs/)が必要です．

Python 3.8 推奨です．

```
git clone https://github.com/Be4rR/serial-monitor.git
cd serial-monitor
poetry install
```

config.jsonの内容を変更します．特に`port`と`baudrate`は環境に合わせて設定する必要があります．
```
{"port": "COM7", "baudrate": 115200, "plot_width": 300, "save_dir": "./data"}
```

実行します．
```
poetry run python script.py
```

![image](https://user-images.githubusercontent.com/44293565/156522146-c4999f10-c134-4d93-8882-59895ac1a4c4.png)
