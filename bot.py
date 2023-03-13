# -*- coding: utf-8 -*-
import json
import logging
import random
import asyncio
import re
from lexicon import LEXICON
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.fsm_storage.memory import MemoryStorage # потом удалить 
from aiogram.dispatcher import FSMContext
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import Dispatcher, filters
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

with open ("key", 'r') as key: 
    BOT_TOKEN = key.read()

# Инициализируем хранилище (создаем экземпляр класса RedisStorage2)
storage: RedisStorage2 = RedisStorage2("192.168.0.102", 6379, db=1)

#storage: MemoryStorage = MemoryStorage()


ingedients_callback: dict = {}
inline_kb1: dict = {}
elements: int = 5

# Подгружаем базы
with open("data.json", 'r') as write_file: 
    b = json.load(write_file)

with open("resipe_data.json", 'r') as write_file: 
    c = json.load(write_file)

with open("goods_data.json", 'r') as write_file: 
    a = json.load(write_file)

# Создаем объекты бота и диспетчера
bot: Bot = Bot(BOT_TOKEN)
dp: Dispatcher = Dispatcher(bot, storage=storage)

class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодейтсвия с пользователем
    find_cocktail = State()        # Состояние поиска коктейля по названию
    choose_category = State()         # Состояние выбора категории продуктов
    choose_goods = State()     # Состояние выбора продуктов
    search_goods = State()      # Состояние поиска продуктов
    choose_goods_search = State()   # Состояния выбора продуктов после поиска
    menu_state = State()       # Состояние нахождения в главном меню
    choose_cocktail = State()   #состояние выбора коктейля после поиска
    yes_or_no_state = State()   #состояние выбора заполнения списка 


#-----------------------------------------
# --------- Стартовая клавиатура ---------
#-----------------------------------------
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.row(KeyboardButton(LEXICON['find_goods_btn']), 
                   KeyboardButton(LEXICON['random_cocktail_btn']))
start_keyboard.add(KeyboardButton(LEXICON['find_cocktail_btn']))
#-----------------------------------------

#-------------------------------------------------------
# --------- Клавиатура с категориями продуктов ---------
#-------------------------------------------------------
markup_goods_cat = ReplyKeyboardMarkup(resize_keyboard=True) 
markup_goods_cat.row(KeyboardButton(LEXICON['exit_menu_btn']))
markup_goods_cat.row(KeyboardButton(LEXICON['search_goods_btn']))
for i in range(len(list(a.keys()))):
    markup_goods_cat.row(KeyboardButton((list(a.keys()))[i])) 
#-------------------------------------------------------

#------------------------------------------------------------
# ----------------- Клавиатура с продуктами -----------------
#------------------------------------------------------------
def process_create_goods_keyboard(text_from_message):
    goods_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    goods_keyboard.row(LEXICON['back_goods_keyboard_btn'])
    for good in a[text_from_message]:
        goods_keyboard.row(KeyboardButton(good))
    return goods_keyboard
#------------------------------------------------------------

#------------------------------------------------------------
# -------------- Клавиатура с выходом из поиска -------------
#------------------------------------------------------------
exit_keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
exit_keyboard.row(KeyboardButton(LEXICON['exit_from_good_search_nodata']))
#------------------------------------------------------------

#---------------------------------------------------------
# -------------- Клавиатура c выбором списка -------------
#---------------------------------------------------------
yes_or_no = ReplyKeyboardMarkup(resize_keyboard=True)
yes_or_no.row(KeyboardButton('Да✅'))
yes_or_no.row(KeyboardButton('Нет❌'))
#---------------------------------------------------------

#---------------------------------------------------------
# ------------ Клавиатура c кнопкой закрыть --------------
#---------------------------------------------------------
close_keyboard = InlineKeyboardMarkup()
close_keyboard.add(InlineKeyboardButton(LEXICON['close_btn'], callback_data=LEXICON['close_callback']))
#---------------------------------------------------------

def process_create_keyboard(ingedients_list, ingredient_callback):
    inline_kb1 = InlineKeyboardMarkup()
    kb_len = len(ingedients_list)
    if kb_len == 1:
        inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] + ingedients_list[0]), 
                        callback_data=('button' + str(1))))
        inline_kb1.add(InlineKeyboardButton((LEXICON['ready_inline_btn']), callback_data='goods_ready'))
        return inline_kb1
    elif kb_len > 1 and kb_len <= 5:
        k = 0
        for item_from_ingredients in ingedients_list:
            inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] + item_from_ingredients), 
                            callback_data=('button' + str(k))))
            k += 1
        inline_kb1.add(InlineKeyboardButton((LEXICON['ready_inline_btn']), callback_data='goods_ready'))
        return inline_kb1
    elif kb_len > 5:
        list_len = len(ingedients_list)
        if list_len%5==0:
            k = 0
            for i in range(-5, 0):
                inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] + ingedients_list[i]), 
                            callback_data=('button' + str(k))))
                k += 1
        else:
            k = 0
            for i in range(-(len(ingedients_list) - (5 * (len(ingedients_list)//5))), 0, 1):
                inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] + ingedients_list[i+list_len]), 
                            callback_data=('button' + str(k))))
                k += 1
        inline_kb1.row((InlineKeyboardButton(LEXICON['back_inline_btn'], callback_data=f'navi_{list_len//5}b')),
                        (InlineKeyboardButton(f'{str((len(ingedients_list)-1)//5+1)}/{str((len(ingedients_list)-1)//5+1)}', 
                        callback_data=f'navi_{str((len(ingedients_list)-1)//5)}p')),
                        (InlineKeyboardButton(LEXICON['next_inline_btn'], callback_data='navi_0n')))
        inline_kb1.add(InlineKeyboardButton((LEXICON['ready_inline_btn']), callback_data='goods_ready'))
        return inline_kb1


def process_create_cocktail_keyboard(cocktail_list, key_type):
    cocktail_keyboard = InlineKeyboardMarkup()
    list_len = len(cocktail_list)
    if list_len > 1 and list_len <= 10:
        for item in cocktail_list:
            cocktail_keyboard.add(InlineKeyboardButton(item, callback_data=item))
        return cocktail_keyboard
    elif list_len > 10:
        if list_len%10 == 0:
            for i in range(-10, 0):
                cocktail_keyboard.add(InlineKeyboardButton(cocktail_list[i], callback_data=cocktail_list[i]))
            return cocktail_keyboard
        else:
            for i in range(-(len(cocktail_list) - (10 * (len(cocktail_list)//10))), 0, 1):
                cocktail_keyboard.add(InlineKeyboardButton(cocktail_list[i+list_len], callback_data=cocktail_list[i+list_len]))

            cocktail_keyboard.row((InlineKeyboardButton(LEXICON['back_inline_btn'], callback_data=f'{key_type}_b')),
            (InlineKeyboardButton(f'{str((len(cocktail_list)-1)//10+1)}/{str((len(cocktail_list)-1)//10+1)}', 
            callback_data=f'{key_type}_{str((len(cocktail_list)-1)//10)}p')),
            (InlineKeyboardButton(LEXICON['next_inline_btn'], callback_data=f'{key_type}_n')))

            return cocktail_keyboard


def menu_navigation(ingredients, page):
    inline_kb1 = InlineKeyboardMarkup()
    list_len = len(ingredients) 
    if list_len < page*elements:
        k = 0
        for i in range(elements*page-elements, (elements*page)-(page*elements-list_len)):
            inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] +ingredients[i]), 
                                                    callback_data=('button' + str(k))))
            k += 1
    elif page*elements<=list_len:
        k = 0
        for i in range(elements*page-5, elements*page):
            inline_kb1.add(InlineKeyboardButton((LEXICON['remove_good_inline_btn'] + ingredients[i]), 
                                                    callback_data=('button' + str(k))))
            k += 1
    inline_kb1.row((InlineKeyboardButton(LEXICON['back_inline_btn'], callback_data=f'navi_{list_len//5}b')),
                    (InlineKeyboardButton(f'{str(page)}/{str((len(ingredients)-1)//5+1)}', callback_data=f'navi_{page}p')),
                    (InlineKeyboardButton(LEXICON['next_inline_btn'], callback_data='navi_0n')))
    inline_kb1.add(InlineKeyboardButton((LEXICON['ready_inline_btn']), callback_data='goods_ready'))
    return inline_kb1


def cocktail_navigation(cocktail_list, page, key_type):
    elements2 = 10
    cocktail_keyboard = InlineKeyboardMarkup()
    list_len = len(cocktail_list)
    if list_len < page*elements2:
        k = 0
        for i in range(elements2*page-elements2, (elements2*page)-(page*elements2-list_len)):
            cocktail_keyboard.add(InlineKeyboardButton((cocktail_list[i]), 
                                                    callback_data=cocktail_list[i]))
            k += 1
    elif page*elements2<=list_len:
        k = 0
        for i in range(elements2*page-elements2, elements2*page):
            cocktail_keyboard.add(InlineKeyboardButton((cocktail_list[i]), 
                                                    callback_data=cocktail_list[i]))
            k += 1
    cocktail_keyboard.row((InlineKeyboardButton(LEXICON['back_inline_btn'], callback_data=f'{key_type}_{list_len//elements2}b')),
                    (InlineKeyboardButton(f'{str(page)}/{str((len(cocktail_list)-1)//elements2+1)}', callback_data=f'{key_type}_{page}p')),
                    (InlineKeyboardButton(LEXICON['next_inline_btn'], callback_data=f'{key_type}_0n')))

    return cocktail_keyboard


async def process_start_command(message: Message, state: FSMContext):
    with open('users.txt', 'a') as user_file:
        user_file.write(f'{message.from_user.id} \n')
        await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        data['start_message'] = (await message.answer(LEXICON['start_messsage'], reply_markup=start_keyboard)).message_id
        data['ingredients'] = []
        data['ingredients_callback'] = 0
        data['list_ingredients_callback'] = []
    await FSMFillForm.menu_state.set()


async def process_random_cocktail(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    step_count = 0
    steps = ''
    cock_index = random.randint(0, len(list(a.keys())))
    for step in list(c[list(c.keys())[cock_index]]):
        step_count = step_count + 1
        steps = steps + str(step_count) + '. ' + step + '\n'
    send_text_random_cock = LEXICON['random_cocktail_text'] + list(b.keys())[cock_index] + '</b> \n'
    for i in range(1, len(b[list(b.keys())[cock_index]])):
        item = b[list(b.keys())[cock_index]][i]
        send_text_random_cock = send_text_random_cock + '->' + '<code>' + item + '</code> \n'
    send_text_random_cock = send_text_random_cock + LEXICON['cocktail_recipe'] + list(b.keys())[cock_index] + '</u> \n<i>' + steps + '</i>'
    await message.answer(send_text_random_cock, parse_mode='HTML', reply_markup=close_keyboard)


async def process_search_cocktail_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            await bot.delete_message(message.chat.id, data['search_cocktail_message'])
        except:
            pass
    await bot.delete_message(message.chat.id, message.message_id)
    await message.answer(LEXICON['search_cocktail_text'], reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(LEXICON['search_cocktail_back_btn'])))
    await FSMFillForm.find_cocktail.set()


async def process_search_cocktail(message: types.Message, state: FSMContext):
    cocktail_search_list = []
    await bot.delete_message(message.chat.id, message.message_id)
    await message.answer(LEXICON['process_search_cocktail_text'], reply_markup=start_keyboard)
    for searching_cock in list(b.keys()):
        if re.search(fr'\b{message.text.lower()}\b', searching_cock.lower()):
            if len(searching_cock) < 33:
                cocktail_search_list.append(searching_cock)
    if cocktail_search_list != []: 
        async with state.proxy() as data:
            try:
                await bot.delete_message(message.chat.id, data['start_message'])
            except:
                pass
            keyboard = process_create_cocktail_keyboard(cocktail_search_list, 'search')
            keyboard.add(InlineKeyboardButton(LEXICON['close_btn'], callback_data=LEXICON['close_callback']))
            data['search_cocktail_message'] = (await message.answer(LEXICON['secces_find_cocktail_text'], reply_markup=keyboard)).message_id
            data['search_page'] = ((len(cocktail_search_list)+9)//10)
            data['search_cocktail'] = cocktail_search_list
            await FSMFillForm.menu_state.set()
    elif cocktail_search_list == []:
        await message.answer(LEXICON['unsecces_find_cocktail_text'], reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(LEXICON['search_cocktail_back_btn'])))



async def process_search_cocktail_back(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            await bot.delete_message(message.from_user.id, data['start_message'])
        except:
            pass
        data['start_message'] = (await message.answer(LEXICON['start_messsage'], reply_markup=start_keyboard)).message_id
    await bot.delete_message(message.chat.id, message.message_id)
    await FSMFillForm.menu_state.set()


async def process_choose_category(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        if data['ingredients'] != []:
            data['yes_or_no_message'] = (await message.answer(LEXICON['yes_or_no_text'], reply_markup=yes_or_no)).message_id
            await FSMFillForm.yes_or_no_state.set()
        elif data['ingredients'] == []:
            data['category_choose_message'] = (await message.answer(LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
            try:
                await bot.delete_message(message.chat.id, data['start_message'])
            except:
                pass
            await FSMFillForm.choose_category.set()


async def process_choose_yes(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['yes_or_no_message'])
        data['category_choose_message'] = (await bot.send_message(message.from_user.id, LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
        data['goods_menu_message'] = (await bot.send_message(message.from_user.id, LEXICON['curent_goods_list_text'], 
        reply_markup=process_create_keyboard(data['ingredients'], data['ingredients_callback']))).message_id
    await FSMFillForm.choose_category.set()


async def process_choose_no(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['yes_or_no_message'])
        data['ingredients'] = []
        data['ingredients_callback'] = 0
        data['list_ingredients_callback'] = []
        data['category_choose_message'] = (await message.answer(LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
        try:
            await bot.delete_message(message.chat.id, data['start_message'])
        except:
            pass
        await FSMFillForm.choose_category.set()


async def process_choose_category_back(message: types.Message, state: FSMContext):
    await message.answer(LEXICON['exit_text'], reply_markup=start_keyboard)
    await bot.delete_message(message.chat.id,  message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['category_choose_message'])
    await FSMFillForm.menu_state.set()


async def process_choose_goods(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    for k in list(a.keys()):
        if message.text == k:
            async with state.proxy() as data:
                await bot.delete_message(message.chat.id, data['category_choose_message'])
                data['goods_choose_message'] = (await message.answer(LEXICON['goods_choose_text'], 
                                                      reply_markup=process_create_goods_keyboard(message.text))).message_id
            await FSMFillForm.choose_goods.set()


async def process_choose_goods_back(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['goods_choose_message'])
        data['category_choose_message'] = (await message.answer(LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
    await FSMFillForm.choose_category.set()


async def process_search_goods_enabled(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['category_choose_message'])
        data['search_goods_message'] = (await message.answer(LEXICON['search_goods_text'], reply_markup=exit_keyboard)).message_id
    await FSMFillForm.search_goods.set()


async def process_search_goods(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    search_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    search_keyboard.row(KeyboardButton(LEXICON['exit_from_good_search']))
    for w in list(a.keys()):
        for p in a[w]:
            if message.text.lower() in p.lower():
                search_keyboard.row(KeyboardButton(p))

    if len(search_keyboard['keyboard']) > 1:
        async with state.proxy() as data:
            await bot.delete_message(message.chat.id, data['search_goods_message'])
            data['search_goods_message'] = (await message.answer(LEXICON['finded_goods_text'], reply_markup=search_keyboard)).message_id
        await FSMFillForm.choose_goods_search.set()
    else:
        async with state.proxy() as data:
            data['search_goods_message'] = (await message.answer(LEXICON['unsecces_find_cocktail_text'], reply_markup=exit_keyboard)).message_id


async def process_search_goods_back(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        await bot.delete_message(message.chat.id, data['search_goods_message'])
        data['category_choose_message'] = (await message.answer(LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
    await FSMFillForm.choose_category.set()


async def process_choose_search_goods_back(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    async with state.proxy() as data:
        data['category_choose_message'] = (await message.answer(LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
        await bot.delete_message(message.chat.id, data['search_goods_message'])
    await FSMFillForm.choose_category.set()


async def process_add_goods(message: types.Message, state: FSMContext):
    await bot.delete_message(message.chat.id, message.message_id)
    for h in list(a.keys()):
        if message.text in a[h]:
            async with state.proxy() as data:
                for one_good in data['ingredients']:
                    if one_good == message.text:
                        alert_message = await message.answer(LEXICON['already_in_list_text'])
                        await asyncio.sleep(3)
                        try:
                            await alert_message.delete()
                        except:
                            pass
                        return
                data['ingredients'].append(message.text)
                data['ingredients_callback'] = data['ingredients_callback'] + 1
                data['list_ingredients_callback'].append(data['ingredients_callback'])
                if len(data['ingredients']) == 1:
                    data['goods_menu_message'] = (await message.answer(LEXICON['curent_goods_list_text'], 
                    reply_markup=process_create_keyboard(data['ingredients'], data['ingredients_callback']))).message_id
                elif len(data['ingredients']) > 1:
                    await bot.edit_message_reply_markup(message.chat.id, data['goods_menu_message'], 
                    reply_markup=process_create_keyboard(data['ingredients'], data['ingredients_callback']))
                data['page'] = ((len(data['ingredients'])+4)//5)
                    

async def process_keyboard_navigation(callback: CallbackQuery, state: FSMContext):
    code = re.findall(r'\d+', callback.data)
    code = int(code[0])
    async with state.proxy() as data:
        del data['ingredients'][((data['page']-1) *5) + code]
        data['ingredients_callback'] = data['ingredients_callback']
        await bot.edit_message_reply_markup(callback.from_user.id, data['goods_menu_message'], 
                                            reply_markup=process_create_keyboard(data['ingredients'], data['ingredients_callback']))
        data['page'] = ((len(data['ingredients'])+4)//5)


async def process_callback_navigation(callback: CallbackQuery, state: FSMContext):
    code = callback.data[-1]
    async with state.proxy() as data:
        if code == 'p':
            pass
            await bot.answer_callback_query(callback.id, text='Страница номер ' + str(data['page']))

        if code == 'b' and data['page'] != 1:
            data['page'] = data['page'] -1
            await bot.edit_message_reply_markup(callback.from_user.id, data['goods_menu_message'],
                                                reply_markup=menu_navigation(data['ingredients'], data['page'])) 
        elif code == 'n' and data['page'] != ((len(data['ingredients'])+4)//5):
            data['page'] = data['page'] + 1
            await bot.edit_message_reply_markup(callback.from_user.id, data['goods_menu_message'],
                                    reply_markup=menu_navigation(data['ingredients'], data['page']))


async def process_cocktail_navigation(callback: CallbackQuery, state: FSMContext):
    code = callback.data[-1]
    async with state.proxy() as data:
        if callback.data.startswith('cocktail'):
            page = data['co_page']
            li = data['cocktails_list']
        elif callback.data.startswith('search'):
            page = data['search_page'] 
            li = data['search_cocktail'] 
        if code == 'p':
            pass
            await bot.answer_callback_query(callback.id, text='Страница номер ' + str(page))
        elif code == 'b' and page != 1:
            page = page -1
        elif code == 'n' and page != ((len(li)+9)//10):
            page = page + 1
        if callback.data.startswith('cocktail'):
            data['co_page'] = page
            keyboard = cocktail_navigation(li, page, 'cocktail')
            keyboard.add(InlineKeyboardButton(LEXICON['edit_goods_text'], callback_data=LEXICON['edit_goods_callback']))
        elif callback.data.startswith('search'):
            data['search_page'] = page
            keyboard = cocktail_navigation(li, page, 'search')
        keyboard.row(InlineKeyboardButton(LEXICON['close_btn'], callback_data=LEXICON['close_callback']))
        try:
            await bot.edit_message_reply_markup(callback.from_user.id, callback.message['message_id'],
                                            reply_markup=keyboard)
        except:
            pass

async def process_find_cocktails(callback: CallbackQuery, state: FSMContext):
    h = []
    async with state.proxy() as data:
        try:
            await bot.delete_message(callback.from_user.id, data['category_choose_message'])
        except:
            pass
        for ind in range(0, len(b)):
            count = 0
            for i in range(1, len(b[list(b.keys())[ind]])):	
                item = b[list(b.keys())[ind]][i]
                cock_goods_len = len(b[list(b.keys())[ind]])-1
                for good_l in data['ingredients']:
                    if good_l != ' ' and good_l == item:
                        count += 1
                        if count == len(data['ingredients']):
                            if len(list(b.keys())[ind]) < 33:
                                h.append(list(b.keys())[ind])

    if h != []:
        cocktail_keyboard = process_create_cocktail_keyboard(h, 'cocktail')
        async with state.proxy() as data:
            data['co_page'] = ((len(h)+9)//10)
            await FSMFillForm.choose_cocktail.set()
            data['cocktails_list'] = h
            cocktail_keyboard.add(InlineKeyboardButton(LEXICON['edit_goods_text'], callback_data=LEXICON['edit_goods_callback']))
            cocktail_keyboard.row(InlineKeyboardButton(LEXICON['close_btn'], callback_data=LEXICON['close_list_callback']))
            await bot.send_message(callback.from_user.id, ('.'), reply_markup=start_keyboard)
            data['message_with_keyboard'] = (await bot.send_message(callback.from_user.id, (LEXICON['secces_find_cocktail_text']), reply_markup=cocktail_keyboard)).message_id
        async with state.proxy() as data:
            try:
                await bot.delete_message(callback.from_user.id, data['goods_choose_message'])
            except:
                pass
            await bot.delete_message(callback.from_user.id, data['goods_menu_message'])
    elif h == []:
        alert_message = await bot.send_message(callback.from_user.id, LEXICON['unseccess_find_text'])
        await asyncio.sleep(3)
        try:
            await alert_message.delete()
        except:
            pass
        return


async def process_close(callback: CallbackQuery, state: FSMContext):
    await bot.delete_message(callback.from_user.id, callback.message['message_id'])


async def process_close_cocktail_list(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        try:
            await bot.delete_message(callback.from_user.id, data['start_message'])
        except:
            pass
        await bot.delete_message(callback.from_user.id, callback.message['message_id'])
        data['start_message'] = (await bot.send_message(callback.from_user.id, LEXICON['start_messsage'], reply_markup=start_keyboard)).message_id
        await FSMFillForm.menu_state.set()


async def process_edit_goods(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        await bot.delete_message(callback.from_user.id, data['message_with_keyboard'])
        data['category_choose_message'] = (await bot.send_message(callback.from_user.id, LEXICON['category_choose_text'], reply_markup=markup_goods_cat)).message_id
        data['goods_menu_message'] = (await bot.send_message(callback.from_user.id, LEXICON['curent_goods_list_text'], 
        reply_markup=process_create_keyboard(data['ingredients'], data['ingredients_callback']))).message_id
        await FSMFillForm.choose_category.set()


async def process_show_recipe(callback: CallbackQuery, state: FSMContext):
    step_count = 0
    steps = ''
    cock_index = random.randint(0, len(list(a.keys())))
    for step in list(c[callback.data]):
        step_count = step_count + 1
        steps = steps + str(step_count) + '. ' + step + '\n'
    send_text_random_cock = LEXICON['random_cocktail_text'] + callback.data + '</b> \n'
    for i in range(1, len(b[callback.data])):
        item = b[callback.data][i]
        send_text_random_cock = send_text_random_cock + '->' + '<code>' + item + '</code> \n'
    send_text_random_cock = send_text_random_cock + LEXICON['cocktail_recipe'] + callback.data + '</u> \n<i>' + steps + '</i>'
    await bot.send_message(callback.from_user.id, send_text_random_cock, parse_mode='HTML', reply_markup=close_keyboard)


# Этот хэндлер будет срабатывать на любые сообщения, кроме тех
# для которых есть отдельные хэндлеры, вне состояний
async def send_echo(message: Message):
    alert_message = await message.reply(text=LEXICON['alert_action'])
    await asyncio.sleep(3)
    try:
        await alert_message.delete()
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    return

dp.register_message_handler(process_start_command,
                            commands='start',
                            state="*")

dp.register_message_handler(process_random_cocktail, 
                            filters.Text(equals=LEXICON['random_cocktail_btn']), 
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.menu_state)

dp.register_message_handler(process_search_cocktail_start, 
                            filters.Text(equals=LEXICON['find_cocktail_btn']), 
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.menu_state)

dp.register_message_handler(process_search_cocktail_back, 
                            filters.Text(equals=LEXICON['search_cocktail_back_btn']), 
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.find_cocktail)

dp.register_message_handler(process_search_cocktail,
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.find_cocktail)

dp.register_message_handler(process_choose_category,
                            filters.Text(equals=LEXICON['find_goods_btn']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.menu_state)

dp.register_message_handler(process_choose_category_back,
                            filters.Text(equals=LEXICON['exit_menu_btn']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.choose_category)

dp.register_message_handler(process_choose_goods,
                            lambda x: x.text != LEXICON['search_goods_btn'],
                            state=FSMFillForm.choose_category)

dp.register_message_handler(process_choose_goods_back,
                            filters.Text(equals=LEXICON['back_goods_keyboard_btn']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.choose_goods)

dp.register_message_handler(process_search_goods_enabled,
                            filters.Text(equals=LEXICON['search_goods_btn']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.choose_category)

dp.register_message_handler(process_search_goods,
                            lambda x: x.text != LEXICON['exit_from_good_search_nodata'] 
                            and x.text != LEXICON['exit_from_good_search'],
                            state=FSMFillForm.search_goods)

dp.register_message_handler(process_search_goods_back,
                            filters.Text(equals=LEXICON['exit_from_good_search_nodata']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.search_goods)

dp.register_message_handler(process_choose_search_goods_back,
                            filters.Text(equals=LEXICON['exit_from_good_search']),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.choose_goods_search)

dp.register_message_handler(process_add_goods,
                            lambda x: x.text != LEXICON['exit_from_good_search']
                            and x.text != LEXICON['back_goods_keyboard_btn'],
                            content_types=types.ContentType.TEXT,
                            state=[FSMFillForm.choose_goods_search, FSMFillForm.choose_goods])

dp.register_callback_query_handler(process_keyboard_navigation,
                                   lambda c: c.data and c.data.startswith('button'),
                                   state=[FSMFillForm.choose_goods, FSMFillForm.choose_category, FSMFillForm.search_goods, FSMFillForm.choose_goods_search])

dp.register_callback_query_handler(process_callback_navigation,
                                   lambda c: c.data and c.data.startswith('navi'),
                                   state=[FSMFillForm.choose_goods, FSMFillForm.search_goods, FSMFillForm.choose_category, FSMFillForm.choose_goods_search])

dp.register_callback_query_handler(process_find_cocktails,
                                   lambda c: c.data and c.data.startswith('goods_ready'),
                                   state=[FSMFillForm.choose_goods, FSMFillForm.search_goods, FSMFillForm.choose_category, FSMFillForm.choose_goods_search])

dp.register_callback_query_handler(process_edit_goods,
                                   lambda c: c.data and c.data.startswith('edit_goods'),
                                   state=[FSMFillForm.choose_cocktail])

dp.register_callback_query_handler(process_close_cocktail_list,
                                   lambda c: c.data and c.data.startswith('close_list'),
                                   state="*")

dp.register_callback_query_handler(process_close,
                                   lambda c: c.data and c.data.startswith('close'),
                                   state="*")

dp.register_message_handler(process_choose_yes,
                            filters.Text(equals='Да✅'),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.yes_or_no_state)

dp.register_message_handler(process_choose_no,
                            filters.Text(equals='Нет❌'),
                            content_types=types.ContentType.TEXT,
                            state=FSMFillForm.yes_or_no_state)

dp.register_callback_query_handler(process_cocktail_navigation,
                                   lambda c: c.data and c.data.startswith('cocktail') or 
                                   c.data and c.data.startswith('search'),
                                   state="*")

dp.register_callback_query_handler(process_show_recipe,
                                   state="*")

dp.register_message_handler(send_echo, content_types='any', state="*")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)