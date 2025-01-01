from constants import Emoji

UNDEFINED_ERROR = 'Простите, вы не можете сделать это сейчас {0}'.format(Emoji.SORRY_FACE)
INCORECT_CHOICE = 'Выбранный вариант не найден{0}, пожалуйста, выберите вариант из предложенного списка {1}'.format(
    Emoji.SEARCH, Emoji.NOTE)
KEYBOARD_INSTRACTION = 'Пожалуйста, выберите из предложенных ниже вариантов\nможете написать номер варианта, или нажать на кнопки ниже{0}'.format(
    Emoji.BUTTONS)
INCORECT_FORMAT = 'Простите, вы ввели сообщенние неправильного формата. {0}'.format(Emoji.SORRY_FACE)
BANNED_TEXT = 'Чат заблокирован!'
WARN_PREFIX = 'Предупреждение #'

ASK_TO_ASNWER_BELLOW = 'Пожалуйста, ответьте на вопрос выше{0}\nИли нажите на кнопку под этим сообщением{1}'.format(
    Emoji.UP_ARROW, Emoji.DOWN_ARROW)
CONTINUE_BUTTON = "Продолжить" + Emoji.OK_BUTTON
CANCEL_BUTTON = "Отмена" + Emoji.STOP

NEED_ADMIN = 'Эту операцию может проводить только владелец группы {0}'.format(Emoji.STOP)
SAY_ABOUT_ASK_QUESTION = '{0} Чтобы начать диалог с консультантом, введите ваш вопрос {1}'.format(Emoji.ADVICE,
                                                                                                  Emoji.PENCIL)
# client
WELCOME_CLIENT = 'Здравствуйте {0}, это чат поддержки покупателей от АвтоЛидер\nНажмите на /setup, чтобы отправить вопрос{1}\nСразу после регистрации, ваш вопрос будут обрабатывать наши консультанты{2}'.format(
    Emoji.HELLO_HAND, Emoji.ENVELOPE, Emoji.SMILY_FACE)
ON_GET_NAME = 'Очень приятно'
ASK_NAME_CLIENT = 'Пожалуйста, назовите свое имя{0}\n{1} Вы можете изменить его потом с помощью /rename'.format(
    Emoji.PLEASE_HANDS, Emoji.ADVICE)
ASK_CITY_CLIENT = 'Назовите свой город{0}'.format(Emoji.CITY_PHOTO)
ASK_POINT_CLIENT = 'Нашли несколько точек в вашем городе {0}\nК какой вы хотите обратиться? \n{1} Вы можете в любой момент изменить свой город с помощью комманды /change_point'.format(
    Emoji.SEARCH, Emoji.ADVICE)
ON_REGISTRATION_CLIENT = 'Большое спасибо, было очень приятно с вами познакомиться{0}\nКакой вопрос вас интересует?'.format(
    Emoji.WINKY_FACE)
ABOUT_CHANGE_DATA_CLIENT = 'Вы можете изменить данные о выбраной точки {0}:\nнажмите /change_point\nМожете изменить ваше имя {1}:\nнажмите /rename'.format(
    Emoji.PIN, Emoji.SILHUETTE)
# consultant
ASK_NAME_CONSULTANT = 'Пожалуйста, устоновите имя которое будет видеть клиент {0} с помощью комманды /set_name <ИМЯ>\n\n{1} (При последующих обращениях повторная устоновка имени не требуется)'.format(
    Emoji.PENCIL, Emoji.ADVICE)
ON_REGISTRATION_CONSULTANT = 'Данные сохранены{0}\n{1} Чтобы изменить введите еще раз /set_name <ИМЯ>'.format(
    Emoji.OK_BUTTON, Emoji.ADVICE)
# point
ONLY_ADMIN = 'Простите, только влалец группы может осуществять эту операцию{0}'.format(Emoji.SORRY_FACE)
SECRET_CODE_PREFIX = 'Пожалуйста, сообщите ваш секретный код {0} управляющему.\nПосле активации вам нужно ввести /start.\nВаш скретный код:'.format(
    Emoji.KEY)
WELCOME_POINT = 'Здравствуйте {0}. Я буду помогать вам связываться с покупателями. Пройдите небольшую регистрацию точки.'.format(
    Emoji.HELLO_HAND)
ASK_WORK_HOURS_POINT = 'Пожалуйста, сообщите время работы точки {0}, когда вы сможете отвечать клиентам {1}?\nНапишите в формате: ЧЧ:ММ-ЧЧ:ММ\n(напишите часовом поясе вашей точки)'.format(
    Emoji.CLOCK, Emoji.PERSON)
ASK_NAME_POINT = 'Какое название будет у точки{0}\n(оно будет высвечиваться при выборе клинтом места, куда будет отправлен его вопрос{1})'.format(
    Emoji.LABEL, Emoji.INCOMING_MESSAGE
)
ON_REGISTRATION_POINT = 'Спасибо! Вы прошли регистрацию {0}\nСкоро в канале будут появлятся вопросы {1}.\n\nЧтобы изменить данные{2} введите /start\nДля удаления{3} группы введите /delete_point\n\n*Чтобы консультант имел возможность отвечать на вопрос, консультанту необходимо ввести /set_name <ИМЯ>'.format(
    Emoji.CELEBRATION, Emoji.ENVELOPE, Emoji.PENCIL, Emoji.FIRE)

NOT_ALL_ANSWERED = 'Простите{0}, операция не может быть выполнена, потому что не все вопросы закрыты{1}'.format(
    Emoji.SORRY_FACE, Emoji.OK_BUTTON)
ON_DELETE_POINT = 'Точка удалена {0}'.format(Emoji.TRASH)
# tasks
# -errors
ERROR_ALREADY_IN_CONVERASTION = 'Не получается {0}, вы сейчас в разговоре с консультантом {1}\nПопросите его, чтобы завершить разговор'.format(
    Emoji.STOP, Emoji.SPEAKING)
# -inlines
ON_TASK_CANCEL = 'Тема разговора отменена{0}'.format(Emoji.TRASH)
ASK_TO_REPEAT_CLIENT = 'Извините {0}! Не могли бы вы повторить свой вопрос?'.format(Emoji.VERY_SORRY_FACE)
ON_TASK_CONTINUE = 'Спасибо! Ваш вопрос уже рассматривается нашими консультантами{0}'.format(Emoji.CONSULTANT)
THANKS_FOR_RATE = 'Большое спасибо за ваше мнение! {0} Мы будем улучшаться. {1}'.format(Emoji.PLEASE_HANDS, Emoji.FIRE)


def gen_confirm_text(city, point, dist):
    confirm = f'Ваш город: <b>{city}</b>, выбранная точка: <b>{point}</b>'
    if dist > 15:
        confirm += "\n<i>Выбранное место начнет работу через <b>{0}ч.{1}м.</b> {2} Но вам могут ответить и раньше{3}</i>.".format(
            dist // 60, dist % 60, Emoji.WAIT, Emoji.RUNNER)

    confirm += '\n\nОтправить вопрос в группу консультантов?{0}\nВыберите один из вариантов ниже{1}'.format(
        Emoji.INCOMING_MESSAGE, Emoji.DOWN_FINGER)
    return confirm


# -conversations
NEW_TASK = Emoji.ENVELOPE + ' Новый вопрос от {name}\n' + Emoji.ADVICE + Emoji.STOP + 'Закрыть тему- /close\n' + Emoji.ADVICE + Emoji.REDIRECT + 'Переадресация-/redirect'
CLOSE_TASK = 'Вопрос закрыт{0}\n{3}Чтобы задать новый вопрос введие его в чат\n\nПожалуйста{1}, оцените нашу работу кнопками ниже {2}'.format(
    Emoji.CORRECT,
    Emoji.PLEASE_HANDS,
    Emoji.DOWN_FINGER, Emoji.ADVICE)
QUICK_CLOSE_TASK = 'Вы быстро завершили тему {0}, вам будут начислены бонусные очки {2}, если клиент поставит оценку {1}'.format(
    Emoji.QUICK, Emoji.STAR, Emoji.FIRE)
GENERAL_CLOSE_TASK = 'Вопрос закрыт {0}, спасибо {1}'.format(Emoji.CORRECT, Emoji.PLEASE_HANDS)
CLENT_ANSWER = '-ответ клиента {0}-'.format(Emoji.CLIENT)
CONSULTANT_ANSWER = 'ответ консультанта {0}:\n'.format(Emoji.CONSULTANT)
ON_NOT_SUPPORTED_TASK = '{0} Данный пост не поддерживается'.format(Emoji.WARNING)

# -redirect messages
REDIRECT_VIDEO = '*Отправлено видео сообщение'
REDIRECT_STICKER = '*Отправлен стикер'

# -redirection
ON_REDIRECTTION_STOP = 'Переадресация остановлена{0}'.format(Emoji.STOP)
SAY_ABOUT_CANCEL = 'Чтобы отменить переадресацию {0}, введите /cancel'.format(Emoji.STOP)
ON_CLIENT_REDIRECTION = 'Пожалуйста, подождите минутку, консультант вас переадресует{0}'.format(Emoji.REDIRECT)

ASK_ABOUT_REDIRECT_CITY = '{0} Выберите один из городов, в который будет переадресован клиент:'.format(Emoji.CITY_PHOTO)
NO_SUITABLE_POINTS = '{0} Простите мы не нашли подходящих точек в этом городе'.format(Emoji.STOP)
ASK_ABOUT_REDIRECT_POINT = '{0} Выберите одну из доступных точек:'.format(Emoji.PIN)
ASK_ABOUT_REDIRECT_TEXT = '{0} Какой текст будет у перенаправляемого сообщения?\n\n{1}(пожалуйста, постарайтесь передать основную цель вопроса, чтобы следующая группа смогла понять мысль обращения)'.format(
    Emoji.LABEL, Emoji.ADVICE)
SUCSESS_REDIRECT = '{0} Переадресация прошла успешно'.format(Emoji.OK_BUTTON)
# watchers
# -leaderboard
CONSULTANT_LEADERBOARD = 'Лидерборд среди консультантов {0}:'.format(Emoji.WINNER_MEDAL)
POINT_LEADERBOARD = 'Лидерборд среди точек {0}:'.format(Emoji.CHAMPION)
CITY_TEXT_LEADERBOARD = '<b><u>Город {0}</u></b>'
CONSULTANT_LEADER = '{tag}\n' + Emoji.PIN + 'точка: <b>{point_name}</b>\n' + Emoji.TARGET + 'ср.оценка:{average:.2f}\n' + Emoji.COUNT + 'кол-во ответов:{count}\n' + Emoji.GIFT + 'бонусов:{bonus}'
POINT_LEADER = Emoji.LABEL + ' Чат: <b>{name}</b>\n' + Emoji.STAR + ' Рейтинг: {rate:.2f}\n' + Emoji.COUNT + ' Колличество ответов: {count}'
# -clear progress
SUCSESS_CLEAR_CONSULTANT = 'Прогресс очищен {0}'.format(Emoji.TRASH)
# -add permition
ON_PERMITION_ADDED = 'Доступ открыт {0}\n{1} Разрешение будет доступно 5 минут'.format(Emoji.OK_BUTTON, Emoji.WARNING)
# -on events
TASK_OPEN_WATCHERS = Emoji.ENVELOPE + 'Получено новое сообщение от пользователя\n{client}\n' + Emoji.RIGHT + 'отправлено в чат {chat}'
TASK_CLOSED_WATCHERS = Emoji.OK_BUTTON + ' Вопрос закрыт консультантом\nКогда клиент оценит работу здесь появится сообщение ' + Emoji.DOWN_ARROW
TASK_RATE_TOPIC_WATCHERS = Emoji.SEARCH + 'Оценка клиента: '
TASK_RATE_GENERAL_WATCHERS = Emoji.BUTTONS + 'Новая оценка пользователя.\nОценка: '
TASK_REDIRECT_WATCHERS = Emoji.REDIRECT + ' Консультант {consultant} перенаправил покупателя в группу:\n' + Emoji.PIN + '{newCity}_{newGroup}\nНовое сообщение ' + Emoji.DOWN_FINGER
REMINDER_HEADER = "{0} Пожалуйста, обратите внимание на клиентов ниже {1}".format(Emoji.RED_LIGHT, Emoji.DOWN_FINGER)
REMINDER_TEXT = '\n{client} ожидает ответа примерно {wait_time:.1f}ч'
