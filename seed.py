import psycopg
import random

DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'hr_department',
    'user': 'nedfedova_hr_user',
    'password': '1405AVT',
    'port': 5432
}

conn = psycopg.connect(
    host=DB_CONFIG['host'],
    dbname=DB_CONFIG['dbname'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    port=DB_CONFIG['port']
)
cur = conn.cursor()

first_names_m = ['Иван', 'Петр', 'Сергей', 'Алексей', 'Дмитрий', 'Андрей', 'Михаил', 'Николай']
first_names_f = ['Анна', 'Мария', 'Елена', 'Ольга', 'Татьяна', 'Наталья', 'Ирина', 'Светлана']
last_names = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Соколов']
positions = ['Менеджер', 'Бухгалтер', 'Программист', 'Аналитик', 'Дизайнер', 'HR-специалист', 'Юрист']

for i in range(110):
    # Жестко задаем пол в зависимости от индекса (четные - М, нечетные - Ж)
    gender = 'М' if i % 2 == 0 else 'Ж'
    
    if gender == 'М':
        full_name = f"{random.choice(last_names)} {random.choice(first_names_m)} {random.choice(last_names[:4])}ович"
    else:
        full_name = f"{random.choice(last_names)}а {random.choice(first_names_f)} {random.choice(last_names[:4])}овна"

    position = random.choice(positions)
    phone = f"+7-9{random.randint(10,99)}-{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}"
    email = f"user{i}@company.ru"
    probation = random.choice([0, 1])
    hire_date = f"202{random.randint(0,4)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

    cur.execute(
        "INSERT INTO employees (full_name, position, gender, phone, email, probation, hire_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (full_name, position, gender, phone, email, probation, hire_date)
    )

conn.commit()
cur.close()
conn.close()
