import httpx

from config import auth

for i in range(0, 150):
    try:
        r = httpx.get(
            f'https://edu.donstu.ru/api/SuggestedModules/Module?moduleId={i}',
            headers={'authorization': auth}
        ).json()
        print(f'{i} - {r["data"]["module"]["name"]}')
    except TypeError:
        pass
    except Exception as e:
        print(f'{i} - {e} - {type(e)}')
'''
9 - Engineering systems: Material, Mechanisms and their properties
22 - Математика часть 3
32 - Основы маркетинга в инженерной экономике
33 - Медиаграмотность: в цифровом мире выживут умные
38 - Основы педагогических знаний
43 - Этика новых технологий
44 - Урбанистика
45 - Спорт
48 - GeekTalks lvl.1
49 - Выйти из городской Башни!
54 - Органическая химия
55 - Астрофизика
59 - Камень, дерево, железо
61 - Elementary, Watson
62 - HardCore
66 - Что внутри игровых консолей? Вскрытие покажет!
68 - Цифровой город
69 - Теория механических аномалий
79 - Экономика
^^
9 - Engineering systems: Material, Mechanisms and their properties
10 - Цифровая грамотность
22 - Математика часть 3
32 - Основы маркетинга в инженерной экономике
33 - Медиаграмотность: в цифровом мире выживут умные
34 - Порядок из хаоса: айдентика
38 - Основы педагогических знаний
39 - Не рычите на собаку
40 - Бизнес английский
43 - Этика новых технологий
44 - Урбанистика
45 - Спорт
48 - GeekTalks lvl.1
49 - Выйти из городской Башни!
52 - Коботы
54 - Органическая химия
55 - Астрофизика
59 - Камень, дерево, железо
60 - Машина Голдберга
61 - Elementary, Watson
62 - HardCore
63 - Intelligence and Meaning in Artificial Brains
66 - Что внутри игровых консолей? Вскрытие покажет!
68 - Цифровой город
69 - Теория механических аномалий
70 - Биотехнология
79 - Экономика
81 - Архитектура и BIM-проектирование
83 - Rapid Farm 2020
85 - GeekTalks:пересборка
86 - "Игротехнические дебюты" или введение в искусство работы модератора проектной работы
87 - Лаборатория лингвокреативности
88 - Архитектура Ростова-на-Дону
89 - Playback theatre
90 - Непримитивные примитивы
91 - Право
92 - Цитология и микробиология
93 - Музыкальные парадоксы: от барокко до рока
94 - Тактики психологического воздействия и защиты
95 - Техника работы в группе
96 - Context & competencies: navigating 21st century professional challenges
97 - Экономические основы бизнес-планирования
98 - Поднебесная: язык и культура Китая
100 - Истина рождается в споре. Критическое мышление для эмоционального здоровья
101 - Город будущего
102 - Реция: страна в центре Европы
103 - HardCore 2021
104 - Farm Robotics
109 - Проектно-аналитическая сессия 2021
110 - Великие книги
111 - Мел
112 - Проектирование Х пространства
113 - Моделирование и САПР
114 - А Я иду по городу
115 - Градостроительная экология
116 - Биологические аспекты биотехнологии
117 - Как понять науку? От идеи до публикации
122 - Последняя миля 2021
124 - Средовые проекты: технологии проектирования изменений
130 - Биотехнологии
'''