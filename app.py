# Импортируем класс Flask и вспомогательные объекты из библиотеки flask
from flask import Flask, request, jsonify, render_template, session
# Импортируем библиотеку psycopg — драйвер для подключения к PostgreSQL
import psycopg
# Импортируем dict_row, чтобы строки из БД возвращались как словари (row['field'])
from psycopg.rows import dict_row
# Импортируем функции для безопасного хеширования и проверки паролей
from werkzeug.security import generate_password_hash, check_password_hash

# Создаем экземпляр Flask-приложения. __name__ говорит Flask, где искать шаблоны и статику
app = Flask(__name__)
# Задаем секретный ключ. Он нужен для подписи сессионных cookie (session). Без него сессии не работают
app.secret_key = 'hr_secret_key_2026_nedfedova'

# Словарь с параметрами подключения к PostgreSQL
DB_CONFIG = {
    'host': 'localhost',          # Хост (локальная машина)
    'dbname': 'hr_department',    # Имя базы данных
    'user': 'nedfedova_hr_user',  # Имя пользователя БД
    'password': '1405AVT',        # Пароль
    'port': 5432                  # Стандартный порт PostgreSQL
}

                                                    ## ПОДКЛЮЧЕНИЕ К БД
# Функция для открытия соединения с БД
def get_db():
    """Открывает соединение с БД и настраивает возврат строк как словарей."""
    # psycopg.connect() подключается к БД с указанными параметрами
    conn = psycopg.connect(
        host=DB_CONFIG['host'],
        dbname=DB_CONFIG['dbname'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        port=DB_CONFIG['port'],
        row_factory=dict_row  # Включаем режим словарей (row['full_name'])
    )
    return conn  # Возвращаем объект соединения
# Функция для создания таблиц при первом запуске
def init_db():
    """Создает таблицы, если их еще нет."""
    conn = get_db()          # Открываем соединение
    cur = conn.cursor()      # Создаем курсор для выполнения SQL-запросов
    # Создаем таблицу users (если её нет)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,                -- Автоинкрементный ID
            username VARCHAR(30) UNIQUE NOT NULL, -- Логин, уникальный и обязательный
            password_hash TEXT NOT NULL           -- Хеш пароля (строка)
        )
    ''')
    # Создаем таблицу employees (если её нет)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,                -- Автоинкрементный ID
            full_name VARCHAR(200) NOT NULL,      -- ФИО
            position VARCHAR(100) NOT NULL,       -- Должность
            gender VARCHAR(1) NOT NULL,           -- Пол ('М' или 'Ж')
            phone VARCHAR(30) NOT NULL,           -- Телефон
            email VARCHAR(100) NOT NULL,          -- Email
            probation INTEGER NOT NULL DEFAULT 0, -- Испытательный срок (0 или 1)
            hire_date DATE NOT NULL               -- Дата устройства (тип DATE)
        )
    ''')
    conn.commit()  # Фиксируем изменения (без commit данные не сохранятся в БД)
    cur.close()    # Закрываем курсор
    conn.close()   # Закрываем соединение

# Вызываем init_db() при импорте модуля. Это нужно, чтобы при запуске сервера таблицы точно были
init_db()

                                                                            ## ВАЛИДАЦИЯ 
# Функция проверки логина
def validate_login(username):
    # Проверяем, что логин не пустой и длина от 3 до 30 символов
    if not username or len(username) < 3 or len(username) > 30:
        return False
    # Множество разрешенных символов (латиница, цифры, знаки препинания)
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=.,')
    # Возвращаем True, если ВСЕ символы логина входят в allowed
    return all(c in allowed for c in username)

# Функция проверки пароля
def validate_password(password):
    # Проверяем, что пароль не пустой и длина от 6 до 50 символов
    if not password or len(password) < 6 or len(password) > 50:
        return False
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=.,')
    return all(c in allowed for c in password)

# Функция проверки данных сотрудника
def validate_employee(data):
    # Список обязательных полей
    required = ['full_name', 'position', 'gender', 'phone', 'email', 'hire_date']
    # Проходим по каждому полю и проверяем, что оно заполнено
    for field in required:
        if not data.get(field) or not str(data[field]).strip():
            return False, f'Поле {field} обязательно'
    # Проверяем, что пол — это 'М' или 'Ж'
    if data['gender'] not in ('М', 'Ж'):
        return False, 'Пол должен быть М или Ж'
    # Проверяем, что в email ровно один символ '@'
    if not data['email'].count('@') == 1:
        return False, 'Некорректный email'
    return True, None  # Всё ок — возвращаем True и None (нет ошибки)

                                                                    ##  МАРШРУТЫ СТРАНИЦ 

@app.route('/')  # Главная страница
def index():
    return render_template('index.html')  # Отдаем HTML-шаблон

@app.route('/login')  # Страница входа
def login_page():
    return render_template('login.html')

@app.route('/register')  # Страница регистрации
def register_page():
    return render_template('register.html')

                                                                    ## ОБРАБОТЧИК JSON-RPC 

@app.route('/api/jsonrpc', methods=['POST'])  # Единая точка входа для всех RPC-запросов
def jsonrpc():
    req = request.get_json()  # Получаем JSON из тела запроса
    # Проверяем, что тело запроса корректно и версия JSON-RPC 2.0
    if not req or req.get('jsonrpc') != '2.0':
        return jsonify({'jsonrpc': '2.0', 'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': None}), 400

    method = req.get('method')      # Имя вызываемого метода
    params = req.get('params', {})  # Параметры (по умолчанию пустой словарь)
    req_id = req.get('id')          # ID запроса (для сопоставления ответа)

    # Диспетчеризация: в зависимости от method вызываем нужную функцию
    if method == 'getEmployees':
        result = method_get_employees(params)
    elif method == 'register':
        result = method_register(params)
    elif method == 'login':
        result = method_login(params)
    elif method == 'logout':
        result = method_logout(params)
    elif method == 'checkAuth':
        result = method_check_auth(params)
    elif method == 'addEmployee':
        result = method_add_employee(params)
    elif method == 'updateEmployee':
        result = method_update_employee(params)
    elif method == 'deleteEmployee':
        result = method_delete_employee(params)
    elif method == 'getEmployeeById':
        result = method_get_employee_by_id(params)
    else:  # Если метод неизвестен — возвращаем ошибку -32601
        return jsonify({'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found'}, 'id': req_id}), 200
    # Если функция вернула ошибку — оборачиваем её в JSON-RPC ответ
    if isinstance(result, dict) and result.get('error'):
        return jsonify({'jsonrpc': '2.0', 'error': result['error'], 'id': req_id}), 200
    # Иначе возвращаем успешный результат
    return jsonify({'jsonrpc': '2.0', 'result': result, 'id': req_id}), 200

                                                                                
                                                                                ## RPC-МЕТОДЫ 
def method_get_employees(params):
    # Извлекаем параметры (offset, search, sort, order)
    offset = int(params.get('offset', 0))          # Смещение (сколько записей пропустить)
    limit = 20                                     # Максимум 20 записей за раз (по заданию)
    search = params.get('search', '').strip()      # Поисковая строка
    sort_field = params.get('sort', 'id')          # Поле для сортировки
    sort_order = params.get('order', 'asc').lower() # Направление ('asc' или 'desc')

    # Белый список полей для сортировки (защита от SQL-инъекций через имя столбца)
    allowed_sort = ['id', 'full_name', 'position', 'gender', 'phone', 'email', 'probation', 'hire_date']
    if sort_field not in allowed_sort:
        sort_field = 'id'  # Если поле не из списка — сортируем по id
    if sort_order not in ('asc', 'desc'):
        sort_order = 'asc'  # Если направление неверное — по возрастанию

    conn = get_db()    # Открываем соединение
    cur = conn.cursor() # Создаем курсор
    query = "SELECT * FROM employees"                      # Базовый запрос
    count_query = "SELECT COUNT(*) as cnt FROM employees"  # Запрос для подсчета
    args = []  # Список параметров для запроса

    if search:  # Если поиск задан
        # Добавляем условие поиска по 4 полям (ILIKE — регистронезависимый LIKE)
        query += " WHERE full_name ILIKE %s OR position ILIKE %s OR email ILIKE %s OR phone ILIKE %s"
        count_query += " WHERE full_name ILIKE %s OR position ILIKE %s OR email ILIKE %s OR phone ILIKE %s"
        pattern = f'%{search}%'  # Шаблон для LIKE
        args = [pattern, pattern, pattern, pattern]

    # Добавляем сортировку и пагинацию (LIMIT/OFFSET)
    query += f" ORDER BY {sort_field} {sort_order} LIMIT %s OFFSET %s"
    args.extend([limit, offset])  # Добавляем limit и offset в параметры

    cur.execute(query, args)      # Выполняем запрос с параметрами
    employees = cur.fetchall()    # Получаем все строки (до 20)

    # Подсчитываем общее количество (для кнопки "Показать ещё")
    if search:
        cur.execute(count_query, args[:len(args)-2])  # Без limit/offset
    else:
        cur.execute(count_query)
    total = cur.fetchone()['cnt']  # Получаем число

    cur.close()   # Закрываем курсор
    conn.close()  # Закрываем соединение
    # Возвращаем словарь с данными
    return {
        'employees': employees,
        'total': total,
        'offset': offset,
        'limit': limit
    }

## РЕГИСТРАЦИЯ
def method_register(params):
    username = params.get('username', '').strip()  # Логин
    password = params.get('password', '')          # Пароль

    # Валидация логина и пароля
    if not validate_login(username):
        return {'error': {'code': -1, 'message': 'Логин: только латиница, цифры, знаки препинания, длина 3-30'}}
    if not validate_password(password):
        return {'error': {'code': -2, 'message': 'Пароль: только допустимые символы, длина 6-50'}}

    conn = get_db()
    cur = conn.cursor()
    # Проверяем, существует ли уже пользователь с таким логином
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone():  # Если нашли — ошибка
        cur.close()
        conn.close()
        return {'error': {'code': -3, 'message': 'Пользователь с таким логином уже существует'}}

    # Генерируем хеш пароля с солью (PBKDF2-SHA256)
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    # Вставляем нового пользователя в БД
    cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
    conn.commit()  # Фиксируем изменения
    cur.close()
    conn.close()
    return {'success': True, 'message': 'Регистрация успешна'}

## АВТОРИЗАЦИЯ
def method_login(params):
    username = params.get('username', '').strip()
    password = params.get('password', '')

    conn = get_db()
    cur = conn.cursor()
    # Ищем пользователя по логину
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    # Если пользователь не найден или пароль неверен — ошибка
    if not user or not check_password_hash(user['password_hash'], password):
        return {'error': {'code': -4, 'message': 'Неверный логин или пароль'}}

    # Сохраняем данные пользователя в сессии (Flask подписывает cookie)
    session['user_id'] = user['id']
    session['username'] = user['username']
    return {'success': True, 'message': 'Вход выполнен', 'username': user['username']}

## ВЫХОД
def method_logout(params):
    session.clear()  # Очищаем сессию (выход)
    return {'success': True, 'message': 'Выход выполнен'}

## ПРОВЕРКА СТАТУСА АВТОРИЗАЦИИ
def method_check_auth(params):
    # Если в сессии есть user_id — пользователь авторизован
    if 'user_id' in session:
        return {'authenticated': True, 'username': session.get('username')}
    return {'authenticated': False, 'username': None}

## ДОБАВЛЕНИЕ СОТРУДНИКА
def method_add_employee(params):
    # Проверка авторизации: если нет user_id — гость не может добавлять
    if 'user_id' not in session:
        return {'error': {'code': -5, 'message': 'Требуется авторизация'}}

    # Валидация входных данных
    valid, err = validate_employee(params)
    if not valid:
        return {'error': {'code': -6, 'message': err}}

    conn = get_db()
    cur = conn.cursor()
    # Вставляем нового сотрудника (используем параметризованный запрос)
    cur.execute(
        "INSERT INTO employees (full_name, position, gender, phone, email, probation, hire_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (params['full_name'], params['position'], params['gender'], params['phone'], params['email'],
         int(params.get('probation', 0)), params['hire_date'])
    )
    conn.commit()
    cur.close()
    conn.close()
    return {'success': True, 'message': 'Сотрудник добавлен'}

## РЕДАКТИРОВАНИЕ СОТРУДНИКА
def method_update_employee(params):
    if 'user_id' not in session:
        return {'error': {'code': -5, 'message': 'Требуется авторизация'}}

    emp_id = params.get('id')
    if not emp_id:
        return {'error': {'code': -7, 'message': 'Не указан id сотрудника'}}

    valid, err = validate_employee(params)
    if not valid:
        return {'error': {'code': -6, 'message': err}}

    conn = get_db()
    cur = conn.cursor()
    # Обновляем данные сотрудника по его id
    cur.execute(
        "UPDATE employees SET full_name=%s, position=%s, gender=%s, phone=%s, email=%s, probation=%s, hire_date=%s WHERE id=%s",
        (params['full_name'], params['position'], params['gender'], params['phone'], params['email'],
         int(params.get('probation', 0)), params['hire_date'], emp_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {'success': True, 'message': 'Данные обновлены'}

## УДАЛЕНИЕ СОТРУДНИКА
def method_delete_employee(params):
    if 'user_id' not in session:
        return {'error': {'code': -5, 'message': 'Требуется авторизация'}}

    emp_id = params.get('id')
    if not emp_id:
        return {'error': {'code': -7, 'message': 'Не указан id сотрудника'}}

    conn = get_db()
    cur = conn.cursor()
    # Удаляем сотрудника по id
    cur.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {'success': True, 'message': 'Сотрудник удален'}

## ПОИСК СОТРУДНИКА
def method_get_employee_by_id(params):
    emp_id = params.get('id')
    if not emp_id:
        return {'error': {'code': -7, 'message': 'Не указан id сотрудника'}}
    conn = get_db()
    cur = conn.cursor()
    # Ищем сотрудника по id (для заполнения формы редактирования)
    cur.execute("SELECT * FROM employees WHERE id = %s", (emp_id,))
    employee = cur.fetchone()
    cur.close()
    conn.close()
    if not employee:
        return {'error': {'code': -8, 'message': 'Сотрудник не найден'}}
    return {'employee': employee}