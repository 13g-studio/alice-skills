import copy
import json
import logging
import random
import sqlite3
import schedule
from git_task import commiting
from threading import Thread
from flask import Flask, request, render_template
from form import AnswQuest
from portrait import portraits, hash_pass

#  не удаляйте этот путь т.к. у меня проблема с открытием data.json
# with open('C:/Users/Daniel/dev/github/alice-skills/Data.json', encoding='utf8') as f:
# альтернатива для вас:
with open('Data.json', encoding='utf8') as f:
    data = json.loads(f.read())['test']  # массив из словарей дат
with open('Data.json', encoding='utf8') as f:
    terms = json.loads(f.read())['terms']  # same из терминов

app = Flask('')

from flask_ngrok import run_with_ngrok

run_with_ngrok(app)
app.config['SECRET_KEY'] = 'alice'
logging.basicConfig(
    filename='example.log',
    format='%(asctime)s %(name)s %(message)s',
    level=logging.INFO
)

# commiting
schedule.every().hour.do(commiting)


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    server = Thread(target=run)
    server.start()


sessionStorage = {}
x = hash_pass('Hello')
# print(x)
# print(unhash_pass(x, 'Hello'))

# реакции для более живого разговора
right = ['Отлично!', 'Правильно!', 'Супер!', 'Точно!', 'Верно!', 'Хорошо!', 'Неплохо!']

wrong = ['Ой!', 'Не то!', 'Ты ошибся!', 'Немного не то!', 'Неверно!', 'Неправильно!', 'Ошибочка!']

_next = ['Далее', 'Следующий вопрос', 'Продолжим', 'Следующее']

wtf = ['Прости, не понимаю тебя', 'Можешь повторить, пожалуйста?', 'Повтори, пожалуйста', 'Прости, не слышу тебя']

goodbye = ['Пока!', 'До встречи!', 'Будем на связи!', 'Рада была пообщаться!', 'Пока-пока!']

hey = ['Привет', 'Приветствую тебя', 'Отличный день сегодня', 'Хорошо, что мы снова встретились', 'Приветик',
       'Здравствуй']


def config(user_id):
    # перемешивание дат и терминов
    arr = copy.deepcopy(data)
    term = copy.deepcopy(terms)
    random.shuffle(arr)
    random.shuffle(term)
    sessionStorage[user_id] = {
        'suggests': [
            "Викторина",
            "Развлечения 🧩",
            "Полезное"
        ],
        'slicedsuggests': [
            "Меню",
            "Не знаю"
        ],
        'test_buttons': [
            "Даты",
            "Картины",
            "Термины",
            "Меню"
        ],
        'want_to_change_nick': False,
        'old_nick': '',
        "nick": None,
        'id': 0,
        'mode': '',
        'lastPic': False,
        # переменные для дат
        'test': arr,
        'lastQ': False,

        # очки для БД
        'test_count': 0,
        'pic_count': 0,
        'ter_count': 0,

        # переменные для терминов
        'term': term,
        'lastT': False,
        'terID': 0
    }


def write_in_base(user_id):
    con = sqlite3.connect("users.db")
    cur = con.cursor()  # Вот тут будем заносить данные в БД
    test_count = sessionStorage[user_id]['test_count']
    pic_count = sessionStorage[user_id]['pic_count']
    ter_count = sessionStorage[user_id]['ter_count']
    cur.execute(f"SELECT * FROM u WHERE nick = '{sessionStorage[user_id]['nick']}';")
    if cur.fetchone() is None:
        id_ = len(cur.execute('SELECT * FROM u').fetchall())
        cur.execute("INSERT OR REPLACE INTO u VALUES (?,?,?,?,?,?);",
                    (
                        id_ + 1,
                        sessionStorage[user_id]['nick'],  # Заглушка для имени
                        test_count,
                        pic_count,
                        ter_count,
                        test_count + pic_count + ter_count
                    )
                    )
    else:
        cur.execute("UPDATE u SET (date_count, pic_count, ter_count, summa) = (?,?,?,?) WHERE nick = ?;",
                    (
                        test_count,
                        pic_count,
                        ter_count,
                        test_count + pic_count + ter_count,
                        sessionStorage[user_id]['nick']
                    )
                    )
    con.commit()
    con.close()


@app.route('/')
def hi():
    return 'Hey, our app works!'


@app.route('/records')
def records():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    persons = cur.execute("SELECT * FROM u").fetchall()
    persons = sorted(persons, key=lambda x: -x[-1])
    return render_template('records.html', title='Рекорды | ЕГЭ', persons=persons)


@app.route('/ask_question', methods=['GET', 'POST'])
def ask_question():
    form = AnswQuest()
    if form.validate_on_submit():
        with open('questions.txt', 'w', encoding='utf-8') as f:
            f.write(f'Вопрос: {form.question.data}; Ответ: {form.answer.data}')
        return 'Ваш вопрос получен. Спасибо!'
    return render_template('ask.html', title='Задать свой вопрос', form=form)


@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        },
    }
    if 'screen' in request.json['meta']['interfaces']:
        handle_dialog(request.json, response)
    else:
        station_dialog(request.json, response)
    return json.dumps(response)


def handle_dialog(req, res):
    user_id = req['session']['user_id']
    if res['response']['end_session'] is True:
        write_in_base(user_id)
    if req['session']['new']:
        config(user_id)
        try:
            con = sqlite3.connect("users.db")
            cur = con.cursor()
            user = cur.execute(f"SELECT * FROM u WHERE nick = '{req['state']['user']['nick']}';").fetchone()

            res['response']['text'] = \
                f"{random.choice(hey)}, {req['state']['user']['nick']}! Продолжим тренировку! " \
                f"Твои очки:\nДаты: {user[2]}\nКартины: {user[3]}\nТермины: {user[4]}."
            sessionStorage[user_id]['nick'] = req['state']['user']['nick']
            sessionStorage[user_id]['test_count'] = user[2]
            sessionStorage[user_id]['pic_count'] = user[3]
            sessionStorage[user_id]['ter_count'] = user[4]

            res['response']['buttons'] = [
                {'title': suggest, 'hide': False}
                for suggest in sessionStorage[user_id]['suggests']
            ]
            res['response']['buttons'].append({'title': 'Рейтинг 🏆', 'hide': False,
                                               'url': 'https://alice-skills-1--t1logy.repl.co/records'})
            res['response']['buttons'].append({'title': 'Уровень 💪🏻', 'hide': False})
            res['response']['buttons'].append({'title': 'Закрыть навык ❌', 'hide': False})

        except Exception:
            res['response']['card'] = {
                "type": "BigImage",
                "image_id": "965417/78be888e04cf5c61fb9a",
                "title": "Привет!",
                "description": 'Я помогу тебе подготовиться к ЕГЭ по истории ✨\n ''Напиши или скажи своё имя '
                               'или никнейм для сохранения результатов: '
            }
            res['response'][
                'text'] = 'Привет! Я помогу тебе подготовиться к ЕГЭ по истории ✨\n ''Напиши или скажи своё имя или ' \
                          'никнейм для сохранения результатов: '
        return

    if sessionStorage[user_id]['nick'] is None:
        tag = str(random.randint(0, 10001))
        if len(req['request']['original_utterance']) > 30:
            res['response']['text'] = 'Ваше имя или никнейм занимает больше 30 символов. Пожалуйста, исправьте.'
        else:
            new_nick = req['request']['original_utterance'] + "#" + tag
            if sessionStorage[user_id]['want_to_change_nick']:
                con = sqlite3.connect("users.db")
                cur = con.cursor()
                print(new_nick, sessionStorage[user_id]['nick'])
                cur.execute(f"UPDATE u SET nick = '{new_nick}' WHERE nick = '{sessionStorage[user_id]['old_nick']}'")
                con.commit()
                con.close()
                sessionStorage[user_id]['want_to_change_nick'] = False
            sessionStorage[user_id]['nick'] = new_nick
            # write_in_base(user_id)
            res['response']['text'] = f'Приятно познакомиться! Твой ник с тэгом: {sessionStorage[user_id]["nick"]}\n' \
                                      'У меня есть несколько режимов, просто нажми на кнопку 👇 или скажи, ' \
                                      'чтобы выбрать их.' \
                                      ' Не забывай, твои ответы влияют на место в рейтинге, будь внимателен! 😁'
            res['response']['buttons'] = [
                {'title': suggest, 'hide': False}
                for suggest in sessionStorage[user_id]['suggests']
            ]
            res['response']['buttons'].append({'title': 'Рейтинг 🏆', 'hide': False,
                                               'url': 'https://alice-skills-1--t1logy.repl.co/records'})
            res['response']['buttons'].append({'title': 'Уровень 💪🏻', 'hide': False})
            res['user_state_update'] = {
                'nick': sessionStorage[user_id]['nick']
            }

        return

    # log
    logging.info(f"------REQUEST COMMAND: {req['request']['command']} DEVICE: {req['meta']['client_id']}\n")

    if 'меню' in req['request']['original_utterance'].lower() or \
            'рейтинг' in req['request']['original_utterance'].lower() or 'помощь' in req['request'][
        'original_utterance'].lower() or 'что ты умеешь' in req['request']['original_utterance'].lower():
        res['response']['text'] = 'У меня есть несколько режимов, просто нажми на кнопку 👇, чтобы выбрать их. ' \
                                  'Не забывай, твои ответы влияют на место в рейтинге, будь внимателен! 😁'
        res['response']['tts'] = res['response']['text'] + 'Если хочешь, чтобы я называла тебя по-другому, скажи ' \
                                                           'сменить имя или сменить ник '
        sessionStorage[user_id]['lastQ'] = False
        sessionStorage[user_id]['lastPic'] = False
        sessionStorage[user_id]['lastT'] = False
        sessionStorage[user_id]['mode'] = ''
        res['response']['buttons'] = [
            {'title': suggest, 'hide': False}
            for suggest in sessionStorage[user_id]['suggests']
        ]
        res['response']['buttons'].append({'title': 'Рейтинг 🏆', 'hide': False,
                                           'url': 'https://alice-skills-1--t1logy.repl.co/records'})
        res['response']['buttons'].append({'title': 'Уровень 💪🏻', 'hide': False})
        res['response']['buttons'].append({'title': 'Закрыть навык ❌', 'hide': False})
        return

    if 'сменить ник' in req['request']['original_utterance'].lower() or \
            'сменить имя' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['old_nick'] = sessionStorage[user_id]['nick']
        sessionStorage[user_id]['nick'] = None
        res['response']['text'] = 'Как я могу тебя называть?'
        sessionStorage[user_id]['want_to_change_nick'] = True
        return

        # ставим режим
    if 'развлечения' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'ресурсы'

    if 'викторина' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'викторина'

    if 'уровень' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'уровень'

    # если в нашем запросе 'закрыть' заканчиваем сессию
    if 'закрыть' in req['request']['original_utterance'].lower():
        write_in_base(user_id)
        res['response']['text'] = random.choice(
            goodbye) + '\nЕсли тебе понравилось, поставь нам оценку 👇. Спасибо :)\nПроверь своё место в рейтинге!\n' \
                       'Ты можешь помочь нам с вопросами! Переходи по вкладке "Задать свой вопрос", и, ' \
                       'может быть, мы его добавим в тест!'
        res['response']['buttons'] = [{
            'title': 'Оценить ⭐️',
            'hide': False,
            'url': 'https://dialogs.yandex.ru/store/skills/1424e7f5-ege-po-istorii'
        },
            {
                'title': 'Рейтинг 🏆',
                'hide': False,
                'url': 'https://alice-skills-1--t1logy.repl.co/records'
            },
            {
                'title': 'Задай свой вопрос 💬',
                'hide': False,
                'url': 'https://alice-skills-1--t1logy.repl.co/ask_question'
            }
        ]
        res['response']['end_session'] = True
        # config(user_id) # на случай если захочет заново играть БЕЗ перезапуска навыка
        return

    if sessionStorage[user_id]['mode'] == 'викторина':

        if 'викторина' in req['request']['original_utterance'].lower():
            res['response']['text'] = 'Добро пожаловать в викторину!'
            res['response']['buttons'] = [
                {'title': suggest, 'hide': False}
                for suggest in sessionStorage[user_id]['test_buttons']
            ]
            return

    if 'даты' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'даты'
    if 'картины' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'картины'
    if 'термины' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'термины'
    if sessionStorage[user_id]['mode'] == 'даты':
        if not sessionStorage[user_id]['lastQ']:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            sessionStorage[user_id]['lastQ'] = True
        else:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            user_answer = req['request']['command'].lower().split(' ')
            right_answer = sessionStorage[user_id]['test'][sessionStorage[user_id]['id'] - 1][
                'answer'].lower().split(
                ' ')

            if len(right_answer) > 1:  # если у нас 2 года
                if right_answer[0] in user_answer and right_answer[1] in user_answer:
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                    sessionStorage[user_id]['test_count'] += 1  # Сохранение очков по датам
                    write_in_base(user_id)
                else:
                    res['response']['text'] = f"{random.choice(wrong)} Правильный ответ: " \
                                              f"в {right_answer[0]}-{right_answer[1]} гг. \n{random.choice(_next)}: {res['response']['text']}"
            else:  # если 1 год
                if right_answer[0] in user_answer:
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                    sessionStorage[user_id]['test_count'] += 1
                    write_in_base(user_id)
                else:
                    res['response'][
                        'text'] = f"{random.choice(wrong)} Правильный ответ: " \
                                  f"в {right_answer[0]} г. \n{random.choice(_next)}: {res['response']['text']}"
        sessionStorage[user_id]['id'] += 1
        res['response']['buttons'] = [
            {'title': suggest, 'hide': True}
            for suggest in sessionStorage[user_id]['slicedsuggests']
        ]

    elif sessionStorage[user_id]['mode'] == 'картины':
        if not sessionStorage[user_id]['lastPic']:
            sessionStorage[user_id]['arrayPic'] = list(portraits)
            random.shuffle(sessionStorage[user_id]['arrayPic'])
            sessionStorage[user_id]['idPic'] = 0
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Кто изображен на фотографии?'
            res['response']['card']['image_id'] = \
                portraits.get(sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic']])
            sessionStorage[user_id]['lastPic'] = True
        else:
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            for ans in sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic'] - 1].lower().split('/'):
                if ans in req['request']['original_utterance'].lower():
                    res['response']['card']['title'] = random.choice(right)
                    sessionStorage[user_id]['pic_count'] += 1  # Сохранение очков по картинкам
                    write_in_base(user_id)
                    break
                else:
                    res['response']['card']['title'] \
                        = f"{random.choice(wrong)} Правильный ответ: " \
                          f"{random.choice(sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic'] - 1].split('/'))}."

        if sessionStorage[user_id]['idPic'] == len(sessionStorage[user_id]['arrayPic']):
            random.shuffle(sessionStorage[user_id]['arrayPic'])
            sessionStorage[user_id]['idPic'] = 0
            res['response']['card']['image_id'] = \
                portraits.get(sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic']])
            res['response']['card']['title'] += ' Кто изображен на фотографии?'
            res['response']['text'] = res['response']['card']['title']
        sessionStorage[user_id]['idPic'] += 1
        res['response']['buttons'] = [
            {'title': suggest, 'hide': True}
            for suggest in sessionStorage[user_id]['slicedsuggests']
        ]

    elif sessionStorage[user_id]['mode'] == 'термины':
        if not sessionStorage[user_id]['lastT']:
            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']
            sessionStorage[user_id]['lastT'] = True
        else:
            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']
            for ans in sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1][
                'answer'].lower().split(
                '/'):
                if ans in req['request']['original_utterance'].lower():
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                    sessionStorage[user_id]['ter_count'] += 1  # Сохранение очков по терминам
                    write_in_base(user_id)
                    break
                else:
                    res['response'][
                        'text'] = f"{random.choice(wrong)} Правильный ответ: " \
                                  f"{sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1]['answer']}. \n" \
                                  f"{random.choice(_next)}: {res['response']['text']}"
        sessionStorage[user_id]['terID'] += 1
        res['response']['buttons'] = [
            {'title': suggest, 'hide': True}
            for suggest in sessionStorage[user_id]['slicedsuggests']
        ]

    elif sessionStorage[user_id]['mode'] == 'ресурсы':

        if 'развлечения' in req['request']['original_utterance'].lower():
            res['response']['buttons'] = [{
                'title': 'Статьи️ 📖',
                'hide': True,
            },
                {
                    'title': 'Музыка 🎵',
                    'hide': True,
                }
            ]
            res['response']['text'] = 'Здесь мы публикуем интересные материалы. Послушаем музыку или почитаем статьи?'
        elif 'музыка' in req['request']['original_utterance'].lower() or 'музыку' in req['request'][
            'original_utterance'].lower():
            res['response']['buttons'] = [{
                'title': 'Статьи️ 📖',
                'hide': True,
            }]
            res['response']['tts'] = "Вот подборка интересной музыки"
            res['response']['text'] = res['response']['tts']
            res['response']['card'] = {
                "type": "ItemsList",
                "header": {
                    "text": "Историческая музыка",
                },
                "items": [
                    {
                        "image_id": "937455/3a9025e4d08f2c295d85",
                        "title": "Хиты СССР",
                        "description": "Плейлист на Яндекс Музыке",
                        "button": {
                            "url":
                                'https://music.yandex.ru/users/sctnStudio/playlists/1002'
                        }
                    },
                    {
                        "image_id": "1521359/94ab576717d5217f7fdb",
                        "title": "Гимны стран мира",
                        "description": "Плейлист на Яндекс Музыке",
                        "button": {
                            "url": 'https://music.yandex.ru/users/sctnStudio/playlists/1004'
                        }
                    },
                    {
                        "image_id": "965417/aa2cbef4a55c41b57322",
                        "title": "Военные песни",
                        "description": "Плейлист на Яндекс Музыке",
                        "button": {
                            "url": 'https://music.yandex.ru/users/sctnStudio/playlists/1001'
                        }
                    }
                ]
            }
        elif 'статьи' in req['request']['original_utterance'].lower():
            res['response']['buttons'] = [
                {
                    'title': 'Музыка 🎵',
                    'hide': True,
                }
            ]
            res['response']['tts'] = "Вот подборка классных исторических статей"
            res['response']['text'] = res['response']['tts']
            res['response']['card'] = {
                "type": "ItemsList",
                "header": {
                    "text": "Полезные статьи",
                },
                "items": [
                    {
                        # "image_id": "937455/3a9025e4d08f2c295d85",
                        "title": "13 лучших книг по истории России",
                        "description": "Источник: Lifehacker.ru",
                        "button": {
                            "url": 'https://lifehacker.ru/knigi-po-istorii/'
                        }
                    },
                    {
                        # "image_id": "1521359/94ab576717d5217f7fdb",
                        "title": "Советы ЕГЭ по истории",
                        "description": "Источник: Учёба.ру",
                        "button": {
                            "url": 'https://www.ucheba.ru/for-abiturients/ege/articles/history'
                        }
                    },
                    {
                        # "image_id": "965417/aa2cbef4a55c41b57322",
                        "title": "Памятки и шпаргалки по истории",
                        "description": "Источник: historystepa.ru",
                        "button": {
                            "url": 'http://historystepa.ru/'
                        }
                    }
                ]
            }
        else:
            res['response']['buttons'] = [{
                'title': 'Статьи️ 📖',
                'hide': True,
            },
                {
                    'title': 'Музыка 🎵',
                    'hide': True,
                }
            ]
            res['response']['text'] = f"{random.choice(wtf)}\nВыбери вариант из предложенных, пожалуйста!"
        res['response']['buttons'].append({'title': 'Закрыть навык ❌', 'hide': True})
        res['response']['buttons'].append({'title': 'Меню', 'hide': True})
        res['response']['buttons'].append({'title': 'Оценить ⭐', 'hide': True,
                                           'url': 'https://dialogs.yandex.ru/store/skills/1424e7f5-ege-po-istorii'})
        return
    elif sessionStorage[user_id]['mode'] == 'уровень':
        test_count = sessionStorage[user_id]['test_count']
        pic_count = sessionStorage[user_id]['pic_count']
        ter_count = sessionStorage[user_id]['ter_count']
        summa = test_count + pic_count + ter_count
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['tts'] = '<speaker audio="alice-sounds-game-win-1.opus">'
        if summa < 20:
            res['response']['text'] = f'Ты еще новичок, 1 уровень! ' \
                                      f'Поднажми: до 2ого уровня осталось {20 - summa} {count_naming(20, summa)}'
            res['response']['card']['image_id'] = '1540737/62bffa1f1c62a4c6812c'
        elif summa < 40:
            res['response']['text'] = f'Круто! 2 уровень. Рекомендую поднажать:' \
                                      f' до 3ого уровня осталось {40 - summa} {count_naming(40, summa)}'
            res['response']['card']['image_id'] = '213044/e3649e3e18880a531e76'
        elif summa < 60:
            res['response']['text'] = f'Ого-го! Ты на третьем уровне. Совсем чуть-чуть до победы, осталось ' \
                                      f'{60 - summa} {count_naming(60, summa)}'
            res['response']['card']['image_id'] = '1652229/aadaf325e34cb47c7401'
        else:
            res['response']['text'] = f'Поздравляю! С увереностью могу назвать тебя настоящим историком!'
            res['response']['card']['image_id'] = '1540737/674b982eaca1f8245da4'
        res['response']['card']['title'] = res['response']['text']
        res['response']['tts'] += res['response']['text']
        res['response']['buttons'] = [
            {'title': suggest, 'hide': True}
            for suggest in sessionStorage[user_id]['slicedsuggests'][:1]
        ]

        res['response']['buttons'].append({'title': 'Оценить ⭐', 'hide': True,
                                           'url': 'https://dialogs.yandex.ru/store/skills/1424e7f5-ege-po-istorii'})
        return
    else:
        res['response']['buttons'] = [
            {'title': suggest, 'hide': False}
            for suggest in sessionStorage[user_id]['suggests'][:3]
        ]
        res['response']['buttons'].append({'title': 'Рейтинг 🏆', 'hide': False,
                                           'url': 'https://alice-skills-1--t1logy.repl.co/records'})
        res['response']['buttons'].append({'title': 'Уровень 💪🏻', 'hide': False})
        res['response']['buttons'].append({'title': 'Закрыть навык ❌', 'hide': False})
        res['response']['text'] = f"{random.choice(wtf)}\nВыбери вариант из предложенных :)"
    return


def count_naming(level, summa):
    if level - summa == 1:
        return 'очко'
    if 2 <= level - summa <= 4:
        return 'очка'
    if 5 <= level - summa <= 20:
        return 'очков'


def station_dialog(req, res):
    user_id = req['session']['user_id']
    if res['response']['end_session'] is True:
        write_in_base(user_id)
    if req['session']['new']:
        config(user_id)
        try:
            con = sqlite3.connect("users.db")
            cur = con.cursor()
            user = cur.execute(f"SELECT * FROM u WHERE nick = '{req['state']['user']['nick']}';").fetchone()

            res['response']['text'] = \
                f"{random.choice(hey)}, {req['state']['user']['nick']}! Продолжим тренировку! В любой момент ты можешь " \
                f"сказать: закрыть, чтобы закончить наш разговор." \
                f"\nВ какой режим ты хочешь поиграть: даты или термины?"

            sessionStorage[user_id]['nick'] = req['state']['user']['nick']
            sessionStorage[user_id]['test_count'] = user[2]
            sessionStorage[user_id]['ter_count'] = user[4]

        except Exception:
            res['response']['text'] = 'Привет! Я помогу тебе подготовиться к ЕГЭ по истории. Так как у тебя устройство ' \
                                      'без экрана или Навигатор, я могу предложить тебе только 2 режима. ' \
                                      'Скажи своё имя для сохранения результатов:'
        return

    if sessionStorage[user_id]['nick'] is None:
        tag = str(random.randint(0, 10001))
        sessionStorage[user_id]['nick'] = req['request']['original_utterance'] + "#" + tag
        res['response']['text'] = f'Приятно познакомиться! Твой ник с тэгом: {sessionStorage[user_id]["nick"]}\n' \
                                  'Если тебе надоест играть, скажи закрыть, а если понадобится помощь, скажи помощь. ' \
                                  'В какой режим сыграем: даты или термины?'
        return

    if 'даты' in req['request']['original_utterance'].lower() or 'да ты' in req['request']['original_utterance'].lower() \
            or 'дата' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'случайные даты'
    if 'термины' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'термины'
    if 'закрыть' in req['request']['original_utterance'].lower() or res['response']['end_session'] == True:
        write_in_base(user_id)
        res['response']['text'] = random.choice(
            goodbye) + '\nЕсли тебе понравилось, поставь нам звёздочки на сайте Яндекс Диалогов. Спасибо :)'
        res['response']['end_session'] = True
        res['user_state_update'] = {
            'nick': sessionStorage[user_id]['nick']
        }
        # config(user_id) # на случай если захочет заново играть БЕЗ перезапуска навыка
        return

    if 'помощь' in req['request']['original_utterance'].lower() or 'что ты умеешь' in req['request'][
        'original_utterance'].lower():
        res['response']['text'] = 'Я буду задавать вопросы в случайном порядке, а ты старайся отвечать правильно! ' \
                                  'У меня есть 2 режима: даты и термины, в какой сыграем?'
        sessionStorage[user_id]['mode'] = ''
        return
    if sessionStorage[user_id]['mode'] == 'случайные даты':
        if not sessionStorage[user_id]['lastQ']:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            sessionStorage[user_id]['lastQ'] = True
        else:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            user_answer = req['request']['command'].lower().split(' ')
            right_answer = sessionStorage[user_id]['test'][sessionStorage[user_id]['id'] - 1]['answer'].lower().split(
                ' ')

            print(right_answer)
            print(user_answer)
            if len(right_answer) > 1:  # если у нас 2 года
                if right_answer[0] in user_answer and right_answer[1] in user_answer:
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                    sessionStorage[user_id]['test_count'] += 1  # Сохранение очков по датам
                    write_in_base(user_id)
                else:
                    res['response']['text'] = f"{random.choice(wrong)} Правильный ответ: " \
                                              f"в {right_answer[0]}-{right_answer[1]} гг. \n{random.choice(_next)}: {res['response']['text']}"
            else:  # если 1 год
                if right_answer[0] in user_answer:
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                    sessionStorage[user_id]['test_count'] += 1
                    write_in_base(user_id)
                else:
                    res['response'][
                        'text'] = f"{random.choice(wrong)} Правильный ответ: " \
                                  f"в {right_answer[0]} г. \n{random.choice(_next)}: {res['response']['text']}"
        sessionStorage[user_id]['id'] += 1

    elif sessionStorage[user_id]['mode'] == 'термины':

        if not sessionStorage[user_id]['lastT']:

            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']

            sessionStorage[user_id]['lastT'] = True

        else:

            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']

            for ans in sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1]['answer'].lower().split(

                    '/'):

                if ans in req['request']['original_utterance'].lower():
                    res['response'][
                        'text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"

                    sessionStorage[user_id]['ter_count'] += 1  # Сохранение очков по терминам

                    write_in_base(user_id)

                    break

            else:

                res['response'][

                    'text'] = f"{random.choice(wrong)} Правильный ответ: " \
 \
                              f"{sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1]['answer']}. \n" \
 \
                              f"{random.choice(_next)}: {res['response']['text']}"
        sessionStorage[user_id]['terID'] += 1
    else:
        res['response']['text'] = f'{random.choice(wtf)}. В какой режим ты хочешь сыграть: даты или термины?'

    res['response']['buttons'] = [
        {'title': 'Помощь', 'hide': True}
    ]


if __name__ == '__main__':
    app.run()
