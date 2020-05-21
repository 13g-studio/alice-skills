import copy
import json
import logging
import random
import sqlite3
from flask import Flask, request
from portrait import portraits, hash_pass, unhash_pass

# не удаляйте этот путь т.к. у меня проблема с открытием data.json
# with open('C:/Users/Daniel/dev/github/alice-skills/Data.json', encoding='utf8') as f:
# альтернатива для вас:
with open('Data.json', encoding='utf8') as f:
    data = json.loads(f.read())['test']  # массив из словарей дат
with open('Data.json', encoding='utf8') as f:
    terms = json.loads(f.read())['terms']  # same из терминов
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

sessionStorage = {}

x = hash_pass('Hello')
print(x)
print(unhash_pass(x, 'Hello'))

# реакции для более живого разговора
right = ['Отлично!', 'Правильно!', 'Супер!', 'Точно!', 'Верно!', 'Хорошо!', 'Неплохо!']

wrong = ['Ой!', 'Не то!', 'Ты ошибся!', 'Немного не то!', 'Неверно!', 'Неправильно!', 'Ошибочка!']

_next = ['Далее', 'Следующий вопрос', 'Продолжим', 'Следующее']

wtf = ['Прости, не понимаю тебя', 'Можешь повторить, пожалуйста?', 'Повтори, пожалуйста', 'Прости, не слышу тебя']


@app.route('/')
def index():
    return 'hello'


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(request.json, response)

    logging.info('Response: %r', request.json)

    return json.dumps(response)


def handle_dialog(req, res):
    user_id = req['session']['user_id']
    # если 1 раз
    if req['session']['new']:
        # перемешивание дат и терминов
        arr = copy.deepcopy(data)
        term = copy.deepcopy(terms)
        random.shuffle(arr)
        random.shuffle(term)
        sessionStorage[user_id] = {
            'suggests': [
                "Даты 🕰",
                "Картины 🌄",
                "Термины 📚",
                "Рейтинг 🏆",
                "Закрыть навык ❌"
            ],
            'slicedsuggests': [
                "Закрыть навык ❌",
                "Меню"
            ],
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
        res['response']['text'] = 'Привет! Я помогу тебе подготовиться к ЕГЭ по истории ✨\n ' \
                                  'Введи свой никнейм для сохранения!'

        # res['response']['buttons'] = [
        #     {'title': suggest, 'hide': False}
        #     for suggest in sessionStorage[user_id]['suggests'][:4]
        # ]
        return

    if sessionStorage[user_id]['nick'] is None:
        tag = str(random.randint(0, 10001))
        sessionStorage[user_id]['nick'] = req['request']['original_utterance'] + "#" + tag

        res['response']['text'] = f'Приятно познакомиться! Твой ник с тэгом: {sessionStorage[user_id]["nick"]}\n' \
                                  'Нажми кнопку "меню"'
        res['response']['buttons'] = [
            {'title': suggest, 'hide': True}
            for suggest in sessionStorage[user_id]['slicedsuggests']
        ]

    if sessionStorage[user_id]['nick'] is not None and req['request']['original_utterance'].lower() != 'меню':
        res['response']['text'] = random.choice(wtf)

    if 'меню' in req['request']['original_utterance'].lower():
        res['response']['text'] = 'Я буду спрашивать у тебя случайную дату, картину или термин. ' \
                                  'За каждый правильный ответ в любом режиме зачисляются очки, будь внимателен! 😁'
        sessionStorage[user_id]['lastQ'] = False
        sessionStorage[user_id]['lastPic'] = False
        sessionStorage[user_id]['lastT'] = False
        # sessionStorage[user_id]['terID'] = 0
        # sessionStorage[user_id]['id'] = 0
        res['response']['buttons'] = [
            {'title': suggest, 'hide': False}
            for suggest in sessionStorage[user_id]['suggests']
        ]
        return

    # ставим режим
    if 'даты' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'случайные даты'

    if 'картины' in req['request']['original_utterance'].lower() or 'потреты' in req['request'][
        'original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'картины'

    if 'термины' in req['request']['original_utterance'].lower():
        sessionStorage[user_id]['mode'] = 'термины'

    if sessionStorage[user_id]['mode'] == 'случайные даты':
        if not sessionStorage[user_id]['lastQ']:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            sessionStorage[user_id]['lastQ'] = True
        else:
            res['response']['text'] = sessionStorage[user_id]['test'][sessionStorage[user_id]['id']]['question']
            if sessionStorage[user_id]['test'][sessionStorage[user_id]['id'] - 1][
                'answer'].lower() in req['request']['original_utterance'].lower():
                res['response']['text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                sessionStorage[user_id]['test_count'] += 1  # Сохранение очков по датам
            else:
                res['response'][
                    'text'] = f"{random.choice(wrong)} Правильный ответ: {sessionStorage[user_id]['test'][sessionStorage[user_id]['id'] - 1]['answer']}. \n{random.choice(_next)}: {res['response']['text']}"

        sessionStorage[user_id]['id'] += 1

    if sessionStorage[user_id]['mode'] == 'картины':
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
            if sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic'] - 1].lower() \
                    in req['request']['original_utterance'].lower():
                res['response']['card']['title'] = random.choice(right)
                sessionStorage[user_id]['pic_count'] += 1  # Сохранение очков по картинкам
            else:
                res['response']['card']['title'] \
                    = f"{random.choice(wrong)} Правильный ответ: {sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic'] - 1]}."

            if sessionStorage[user_id]['idPic'] == len(sessionStorage[user_id]['arrayPic']):
                random.shuffle(sessionStorage[user_id]['arrayPic'])
                sessionStorage[user_id]['idPic'] = 0
            res['response']['card']['image_id'] = \
                portraits.get(sessionStorage[user_id]['arrayPic'][sessionStorage[user_id]['idPic']])
            res['response']['card']['title'] += ' Кто изображен на фотографии?'
        res['response']['text'] = ''
        sessionStorage[user_id]['idPic'] += 1

    if sessionStorage[user_id]['mode'] == 'термины':
        if not sessionStorage[user_id]['lastT']:
            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']
            sessionStorage[user_id]['lastT'] = True
        else:
            res['response']['text'] = sessionStorage[user_id]['term'][sessionStorage[user_id]['terID']]['question']
            if sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1][
                'answer'].lower() in req['request']['original_utterance'].lower():
                res['response']['text'] = f"{random.choice(right)} {random.choice(_next)}: {res['response']['text']}"
                sessionStorage[user_id]['ter_count'] += 1  # Сохранение очков по терминам
            else:
                res['response'][
                    'text'] = f"{random.choice(wrong)} Правильный ответ: {sessionStorage[user_id]['term'][sessionStorage[user_id]['terID'] - 1]['answer']}. \n{random.choice(_next)}: {res['response']['text']}"
        sessionStorage[user_id]['terID'] += 1

    # если в нашем запросе 'закрыть' заканчиваем сессию
    if 'закрыть' in req['request']['original_utterance'].lower():
        res['response']['text'] = 'Пока!'
        res['response']['end_session'] = True
        con = sqlite3.connect("users.db")
        cur = con.cursor()  # Вот тут будем заносить данные в БД
        test_count = sessionStorage[user_id]['test_count']
        pic_count = sessionStorage[user_id]['pic_count']
        ter_count = sessionStorage[user_id]['ter_count']
        id_ = len(cur.execute("SELECT * FROM u").fetchall())
        cur.execute("INSERT INTO u VALUES (?,?,?,?,?,?)",
                    (
                        id_ + 1,
                        'user_id',
                        sessionStorage[user_id]['nick'],  # Заглушка для имени
                        test_count,
                        pic_count,
                        ter_count,
                        test_count + pic_count + ter_count
                    )
                    )
        con.commit()
        return

    res['response']['buttons'] = [
        {'title': suggest, 'hide': True}
        for suggest in sessionStorage[user_id]['slicedsuggests']
    ]


if __name__ == '__main__':
    app.run()
