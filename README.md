# geekon-game

Создать виртуальное окружение:
```
$ virtualenv env -p python2
```

Активировать окружение и установить пакеты:
```
$ source env\bin\activate
$ pip install -r requirements.txt
```

Создать БД:
```
$ python dbstates\join_game.py
```

Запустить сервер:
```
$ python run.py
```

Залогиниться под пользователя с `id == 1`

