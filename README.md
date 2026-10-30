# QazCargo — зертханалық жұмыстар 1 және 2

**Даурбаев Арсен · ИС-24А**

Бұл репозиторий бұрын жасалған QazCargo жүк тасымалдау жүйесін жалғастырады.
Негізгі сайт — Flask + SQL Server; зертханалық кеңейтім — FastAPI + SQLModel + Streamlit.
Бастапқы веб-интерфейс, авторизация, жеткізу, карта және SQL миграциялары сақталған.

## Зертхананы іске қосу

1. `LAB_SETUP.bat` — тәуелділіктерді орнатады және оқу базасын толтырады.
2. `LAB_API.bat` — FastAPI: <http://127.0.0.1:8000/docs>.
3. Басқа терезеде `LAB_UI.bat` — Streamlit: <http://127.0.0.1:8501>.

Негізгі QazCargo бұрынғыдай `START.bat` арқылы ашылады: <http://127.0.0.1:5000>.
Оны алғаш орнату нұсқаулығы — [README_KZ.md](README_KZ.md).

Зертханалық модуль `labs/lab_1_2/database.db` файлын қолданады. Ондағы барлық
клиенттер мен тапсырыстар — жасанды оқу мысалдары. Бұл файл SQL Server-дегі
QazCargo базасымен синхрондалмайды және негізгі сайттың деректерін өзгертпейді.
Базаны GitHub-тан жүктеудің қажеті жоқ: оны `seed.py` қайта жасайды.

## Қосылған құрылым

```text
backend/                    негізгі Flask сервері
database/                   негізгі SQL Server схемасы және миграциялар
web/                        негізгі QazCargo интерфейсі
labs/lab_1_2/
  database/models.py        SQLModel модельдері және Relationship
  database/db.py            SQLite engine, init_db, session
  routers/orders.py        оқу API маршрутизаторлары
  main.py                   FastAPI қолданбасы
  frontend.py               Streamlit интерфейсі
  seed.py                   әр кестеге 3–5 жазба
  verify_db.py              FK және байланыстарды тексеру
  test_lab.py               оқшауланған автоматты тесттер
docs/labs/                  ER, есеп, талаптар және тексеру нәтижесі
```

## Пәндік аймақ және байланыстар

Төрт негізгі нысан: **Clients, Orders, CargoTypes, CargoItems**.
Clients → Orders — 1:N. Orders ↔ CargoTypes — CargoItems арқылы N:M.
CargoItems салмақ, көлем және дана санын сақтайтын байланыс нысаны болып табылады.
Бір тапсырыста бір жүк түрінің бірнеше позициясы болуы мүмкін, сондықтан оның жеке PK-і бар.
`cargo_types` және `orders` көпке-көп ORM атрибуттары `viewonly=True`:
жаңа позиция барлық міндетті өрістермен CargoItem арқылы қосылады.

Бағыт пен тариф FK-ларын сақтау үшін төрт көмекші кесте енгізілген:
Cities, Routes, VehicleTypes, Tariffs. Барлығы 8 оқу кестесі, 8 FK, 26 жазба.
Бұл — негізгі жүйенің 19 кестелік схемасының оқу бөлігі. SQL Server триггерлері,
тарифті қайта есептеу, толық мәртебе ауысу ережелері және аккаунттар бұл модульге көшірілмеген.
API тек оқу операцияларын ұсынады. Оқу маршруттарының қашықтықтары шартты.

![QazCargo оқу ER диаграммасы](docs/labs/qazcargo-er.png)

## PowerShell командалары

QazCargo түбірлік қалтасында:

```powershell
py -m venv .venv  # тек орта әлі жоқ болса
.\.venv\Scripts\python.exe -m pip install -r requirements-labs.txt
.\.venv\Scripts\python.exe -m labs.lab_1_2.seed
.\.venv\Scripts\python.exe -m labs.lab_1_2.verify_db
.\.venv\Scripts\python.exe -m unittest labs.lab_1_2.test_lab -v
.\.venv\Scripts\python.exe -m uvicorn labs.lab_1_2.main:app --host 127.0.0.1 --port 8000
# басқа терминалда
.\.venv\Scripts\python.exe -m streamlit run labs/lab_1_2/frontend.py --server.address 127.0.0.1
```

Seed бос базаны бір транзакциямен толтырады; толық базаға қайта орындалғанда
жазбаларды қоспайды және өзгертпейді. Жартылай толтырылған база болса, қатемен тоқтайды.
`echo=True` SQL сұрауларын консольде көрсетеді. Әр SQLite қосылымында FK тексеруі қосылады.

## Зертханалық жұмыстардың нәтижесі

- 1-жұмыс: QazCargo тақырыбы, ER диаграммасы, VS Code ортасы, venv, GitHub, қабатты құрылым.
- 2-жұмыс: SQLModel PK/FK, 1:N және N:M, init_db, seed, нақты SQLite файлы, тексерулер.
- Толық есеп және бақылау сұрақтары: [docs/labs](docs/labs).
- AI қолдану сұраулары: [ai-prompts.txt](docs/labs/ai-prompts.txt).
- Бастапқы Flask жобасының нұсқаулығы: [README_KZ.md](README_KZ.md).
- Тексеру: зертхананың 8 тесті және бастапқы жобаның 62 тесті өтті;
  FastAPI HTTP және Streamlit AppTest сәтті. [Нәтижелер](docs/labs/verification.txt).

`.env`, виртуалды орта, дерекқорлар, backup, ZIP және журналдар Git-ке қосылмайды.
