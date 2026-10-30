"""Build the Kazakh report from actual SQL metadata using python-docx.
Run with the Codex bundled document Python runtime, not the app virtualenv.
"""
from pathlib import Path
import json,re
from collections import defaultdict
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs';OUT.mkdir(exist_ok=True)
SCHEMA=json.loads((OUT/'schema.json').read_text(encoding='utf-8-sig'))
NAMES={'OrderDrafts':'Тапсырыс черновиктері','Notifications':'Жеке хабарландырулар','Clients':'Клиенттер','Cities':'Қалалар','VehicleTypes':'Көлік түрлері','Vehicles':'Көліктер','Drivers':'Жүргізушілер','Routes':'Бағыттар','CargoTypes':'Жүк түрлері','Tariffs':'Тарифтер','Orders':'Тапсырыстар','CargoItems':'Жүк позициялары','Trips':'Рейстер','Payments':'Төлемдер','OrderStatusHistory':'Мәртебелер тарихы','Users':'Аккаунттар','Documents':'Құжаттар','SupportTickets':'Қолдау өтініштері','TicketMessages':'Қолдау хаттары'}
MEANING={
'Latitude':('WGS84 ендік, градус; координат жоқ болса NULL','51.1801'),
'Longitude':('WGS84 бойлық, градус; координат жоқ болса NULL','71.44598'),
'Region':('КАТО бойынша өңір','Астана қаласы'),
'GeoSourceID':('Координат дереккөзіндегі ID','geonames:1526273'),
'GeoSourceURL':('Координаттың бастапқы дереккөзі','https://www.geonames.org/1526273/'),
'DistanceSource':('Автожол қашықтығының дереккөзі; қолмен өзгерсе NULL','OSRM / OpenStreetMap · driving'),
'DistanceUpdatedAt':('Қашықтық дерегінің алынған күні','2026-10-29'),
'DraftID':('Черновик нөмірі','1'),
'DraftKey':('Клиент жасаған UUID; қайталап жіберуді таниды','UUID'),
'Payload':('Толтырылмаған тапсырыстың JSON деректері','{}'),
'Step':('Форманың қадамы, 0–3','1'),
'Revision':('Қатар өңдеуді тексеретін нұсқа','2'),
'SubmittedOrderID':('Жіберілген тапсырысқа сілтеме; черновикте NULL','NULL'),
'SenderName':('Жіберушінің аты-жөні', 'Оқу жіберушісі'),
'SenderPhone':('Жіберушінің телефоны', '+77010000001'),
'PickupAddress':('Жүкті алу мекенжайы', 'Оқу көшесі 10'),
'RecipientName':('Алушының аты-жөні', 'Оқу алушысы'),
'RecipientPhone':('Алушының телефоны', '+77010000002'),
'DeliveryAddress':('Жеткізу мекенжайы', 'Оқу көшесі 20'),
'PickupWindowStart':('Жергілікті алу аралығының басы', '09:00'),
'PickupWindowEnd':('Жергілікті алу аралығының соңы', '12:00'),
'TrackingCode':('Кездейсоқ 64 таңбалы ашық бақылау коды', '32 кездейсоқ байттың HEX мәні'),
'NotificationID':('Хабарландырудың ішкі нөмірі', '1'),
'EventType':('Хабарландыру оқиғасы', 'status_changed'),
'ReadAt':('Оқылған сәт, UTC; оқылмаса NULL', 'NULL'),

 'ClientID':('Клиенттің ішкі нөмірі','1'),'CityID':('Қаланың ішкі нөмірі','1'),'VehicleTypeID':('Көлік түрінің нөмірі','1'),
 'VehicleID':('Көліктің нөмірі','1'),'DriverID':('Жүргізушінің нөмірі','1'),'RouteID':('Бағыттың нөмірі','1'),'CargoTypeID':('Жүк түрінің нөмірі','1'),'TariffID':('Тарифтің нөмірі','1'),
 'OrderID':('Тапсырыстың нөмірі','1'),'CargoItemID':('Жүк позициясының ішкі нөмірі','1'),'TripID':('Рейстің ішкі нөмірі','1'),'PaymentID':('Төлемнің ішкі нөмірі','1'),'HistoryID':('Тарих оқиғасының нөмірі','1'),'UserID':('Аккаунттың ішкі нөмірі','1'),'DocumentID':('Құжаттың ішкі нөмірі','1'),'TicketID':('Қолдау өтінішінің нөмірі','1'),'MessageID':('Хабарламаның нөмірі','1'),
 'Name':('Атауы не клиент аты','Астана / Оқу клиенті'),'FullName':('Адамның толық аты','Оқу жүргізушісі 1'),'Phone':('Байланыс телефоны','Оқу үлгісі'),'Email':('Email мекенжайы','client@example.kz'),'Address':('Жеткізу не байланыс мекенжайы','Оқу мекенжайы'),
 'CreatedAt':('Жасалған сәт, UTC','2026-10-18 12:00:00'),'PlateNumber':('Бірегей көлік нөмірі','DEMO-001'),'Brand':('Көлік маркасы','Volvo · оқу үлгісі'),'CapacityKg':('Ең жоғары жүк салмағы, кг','20000.00'),'IsActive':('Қолдануға рұқсат белгісі','1 = белсенді'),
 'LicenseNumber':('Бірегей жүргізуші куәлігі','DEMO-LIC-001'),'FromCityID':('Жөнелту қаласына сілтеме','1 = Астана'),'ToCityID':('Жеткізу қаласына сілтеме','2 = Шымкент'),'DistanceKm':('Оқу қашықтығы, км','1500.00'),'Description':('Жүк не түр сипаттамасы','Қапталған оқу жабдығы'),
 'BasePrice':('Бастапқы есептік баға, ₸','15000.00'),'PricePerKm':('Бір км үшін баға, ₸','120.00'),'PricePerKg':('Бір кг үшін баға, ₸','15.00'),'OrderNumber':('Сервер жасаған сыртқы бірегей нөмір','QZ- және UUID бөлігі'),'OrderDate':('Тапсырыс берілген сәт, UTC','2026-10-18 12:00:00'),'PickupDate':('Жергілікті күнтізбедегі алу күні','2026-11-20'),
 'Status':('Жазбаның рұқсат етілген күйі','New / Planned / Open'),'Notes':('Тапсырысқа қосымша түсінік','Тиеу орнын келісу'),'QuotedAmount':('Сақталған тарихи баға, ₸','196503.75'),'WeightKg':('Позициядағы барлық қаптаманың салмағы, кг','100.25'),'VolumeM3':('Позицияның жалпы көлемі, м³','1.125'),'Quantity':('Қаптама саны; салмаққа көбейтілмейді','4'),
 'DepartureAt':('Рейстің шығу сәті, UTC','2026-11-19 19:30:00'),'ArrivalAt':('Рейстің келу сәті, UTC','2026-11-20 07:00:00'),'Amount':('Тіркелген төлем сомасы, ₸','1000.00'),'PaidAt':('Төлем тіркелген сәт, UTC','2026-10-18 12:05:00'),'Method':('Төлемді есепке алу тәсілі','Cash / Card / Transfer'),'Note':('Төлем не тарих түсіндірмесі','Оқу төлемі'),
 'OldStatus':('Алдыңғы күй; бірінші оқиғада NULL','New'),'NewStatus':('Жаңа күй','Confirmed'),'ChangedAt':('Күй өзгерген сәт, UTC','2026-10-18 12:10:00'),'PasswordHash':('Salt-пен жасалған scrypt хеші; ашық пароль емес','scrypt:… [хеш]'),'Role':('Сервер тексеретін рөл','admin / client'),'AuthVersion':('Сессияны қайтарып алу нұсқасы','1, пароль өзгерсе 2'),'FailedAttempts':('Қате кіру әрекеттерінің саны','0–5'),'LockedUntil':('Уақытша кіру шектеуінің UTC соңы','NULL не UTC уақыт'),
 'Title':('Құжаттың интерфейстегі атауы','Тасымал шарты'),'OriginalName':('Түпнұсқа файл атауы','contract.pdf'),'MediaType':('Тексерілген MIME түрі','application/pdf'),'Category':('Құжат санаты','contract'),'OwnerUserID':('Файлды жүктеген аккаунт','2'),'FileSize':('Файл байттарының саны','2048'),'Content':('Файлдың нақты бинарлық байттары','0x25504446…'),
 'Subject':('Қолдау өтінішінің тақырыбы','Жеткізу туралы сұрақ'),'UpdatedAt':('Соңғы жауап/күй өзгерісінің UTC уақыты','2026-10-18 13:00:00'),'Body':('Қолдау хабарламасының таза мәтіні','Жүктің мәртебесін түсіндіріңіз')}
FILES={
 'backend/usability.py':'Рөлге сай іздеу, жеке черновик және қайталанбайтын жіберу API.',
 'web/wizard.js':'Төрт қадамды форма, автоматты сақтау және тексеру.',
 'web/search.js':'Ctrl+K іздеу және нәтижеден карточка ашу.',
 'database/05_order_drafts.sql':'Черновик кестесін деректерді өшірмей қосатын миграция.',
 'run.py':'Толық Visual Studio үшін Python entry point.',
 'backend/app.py':'Flask қолданбасын жинайды, HTTP беттерін береді, CSRF/host/қате өңдеуді орнатады; Waitress серверін іске қосады.',
 'backend/db.py':'pyodbc қосылымы, SQL параметрлері, нәтижелер, транзакция және write құлпы.',
 'backend/auth.py':'Кіру, тіркелу, пароль хеші, қате әрекет шектеуі, AuthVersion, рөл және бұғаттау.',
 'backend/schema.py':'Каталог allowlist-і, өріс типтері, мәтін/сан/email/күн валидациясы және жергілікті уақытты UTC-ге түрлендіру.',
 'backend/service.py':'Тапсырыс иелігі, Decimal баға, жүк, мәртебе және рейс операциялары.',
 'backend/portal.py':'Public каталог, әкімші CRUD, клиент профиль/тапсырыс, төлем, қолдау, есеп және CSV API.',
 'backend/documents.py':'Файл тексеруі, SQL байт сақтау, иелік тексеруі және қауіпсіз preview.',
 'backend/install.py':'Алғашқы .env, SQL batch орындау, COPY_ONLY backup, VERIFYONLY және дәл атпен reset.',
 'backend/manage.py':'Жергілікті консольден әкімші жасау/пароль қалпына келтіру және резерв.',
 'backend/errors.py':'Біркелкі код/HTTP мәртебесі/өріс бар қате моделі.',
 'web/index.html':'Басты бет, калькулятор, бағыттар, қызметтер, қадамдар.',
 'web/login.html':'Кіру мен клиент тіркеу бетінің қаңқасы.',
 'web/admin.html':'Бөлек әкімші кабинетінің қаңқасы.',
 'web/customer.html':'Бөлек клиент кабинетінің қаңқасы.',
 'web/styles.css':'Адаптивті дизайн, форма, кесте, мәзір және диалог стилі.',
 'web/i18n.js':'KK/RU/EN интерфейс, мәртебе, сервер қатесі және форма атаулары.',
 'web/shared.js':'fetch, CSRF, сессия, ортақ форма/кесте/диалог, сан/уақыт пішімі, баспа.',
 'web/public.js':'Басты калькулятор және кіру/тіркелуден кейін таңдауларды тасымалдау.',
 'web/workspace.js':'Кабинет навигациясы, бөлім маршруты және қауіпсіз автоматты жаңарту.',
 'web/orders.js':'Шолу, тапсырыс тізімі/формасы/карточкасы, жүк, рейс, төлем және баспа.',
 'web/catalogs.js':'SQL анықтамалықтарын схема бойынша басқару формалары.',
 'web/office.js':'Файл жүктеу/TXT жасау/preview және толық есептер.',
 'web/account.js':'Профиль, пароль, аккаунт бұғаттау және қолдау хаттары.',
 'web/print.css':'A4 бет, қайталанатын кесте тақырыбы, баспа жиектері.',
 'web/print.js':'Сурет пен қаріп дайын болғанда стандартты print терезесін ашады.',
 'database/01_create_database.sql':'Базалық 17 кесте, 21 FK, индекстер, view, функция, рәсімдер және триггерлер.',
 'database/02_seed_catalogs.sql':'Тек анықтамалық оқу деректері; клиент/аккаунт/тапсырыс жасамайды.',
 'database/03_verify.sql':'SSMS-та нақты сайт дерегін JOIN/SELECT арқылы тексеру.',
 'tests/test_integration.py':'Нақты SQL Server интеграциялық және қатар орындалу сынақтары.',
 'tests/test_installer.py':'Қауіпті reset аттарын, backup қатесін және GO тоқтауын unit деңгейде тексереді.',
 'tools/build_pages.py':'Төрт статикалық HTML entry point-ті қайта құру құралы; күнделікті іске қосуға қажет емес.',
 'tools/build_document.py':'Осы Word құжатының генераторы.',
 'tools/build_diagrams.py':'21 FK байланысын үш ER көрінісіне салады.',
 'tools/package_project.py':'Құпия файлдарды қоспай ZIP жасап, SHA256 арқылы тексереді.',
 'tools/check_frontend.mjs':'JavaScript синтаксисі мен үш тіл кілттерінің толықтығын тексереді.',
 'tools/export_schema.py':'SQL sys каталогынан құжатқа арналған метадеректерді шығарады.',
 'tools/ui_sandbox.py':'Браузер QA үшін бөлек уақытша SQL база және 5001 порты; жұмыс базасын толтырмайды.'}

def sqltype(c):
    typ=c['type'].upper()
    if typ in ('NVARCHAR','VARCHAR','VARBINARY'):
        length=c['max_length'];length=length//2 if typ=='NVARCHAR' and length!=-1 else length
        typ+='('+('MAX' if length==-1 else str(length))+')'
    elif typ in ('DECIMAL','NUMERIC'):typ+=f"({c['precision']},{c['scale']})"
    elif typ in ('DATETIME2','TIME'):typ+=f"({c['scale']})"
    return typ

def keys(table,c):
    name=c['name'];parts=[]
    if c['is_identity']:parts.append('PK; IDENTITY(1,1)')
    for fk in table['foreign_keys']:
        if fk['column_name']==name:parts.append('FK → '+fk['referenced_table']+'.'+fk['referenced_column'])
    groups=defaultdict(list)
    for i in table['indexes']:
        if i['is_unique'] and not i['is_primary_key'] and not i['is_included_column']:groups[i['name']].append(i)
    for group in groups.values():
        if any(i['column_name']==name for i in group):
            text='UNIQUE'+(' топ: '+', '.join(i['column_name'] for i in group) if len(group)>1 else '')
            if group[0]['filter_definition']:text+='; тек NULL емес'
            parts.append(text)
    if c['default_value']:parts.append('DEFAULT '+c['default_value'])
    return '; '.join(parts) or '—'

from build_diagrams import build as diagrams

doc=Document();sec=doc.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
    st=doc.styles[name];st.font.name='Arial';st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_after=Pt(7)
doc.styles['Normal'].font.size=Pt(10.5);doc.styles['Normal'].paragraph_format.line_spacing=1.14
doc.styles['Title'].font.size=Pt(28)
for name,size in [('Heading 1',18),('Heading 2',13),('Heading 3',11)]:doc.styles[name].font.size=Pt(size)
doc.core_properties.title='QazCargo жүк тасымалдауды басқару жүйесінің түсіндірмесі'
doc.core_properties.author='';doc.core_properties.subject='19 кестелі SQL Server және Python Flask оқу жобасы'
header=sec.header.paragraphs[0];header.text='QazCargo   |   Түсіндірме құжат';header.runs[0].font.size=Pt(8)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('QazCargo  •  ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
for r in footer.runs:r.font.size=Pt(8)

def p(text,style=None):return doc.add_paragraph(text,style)
def h(text,level=1):return doc.add_heading(text,level)
def code(text):
    para=p(text);para.paragraph_format.space_before=Pt(5);para.paragraph_format.space_after=Pt(9)
    for run in para.runs:run.font.name='Consolas';run.font.size=Pt(8.5)
    return para
def table(headers,rows,widths=None):
    tb=doc.add_table(rows=1, cols=len(headers));tb.alignment=WD_TABLE_ALIGNMENT.CENTER;tb.autofit=False
    widths=widths or [17/len(headers)]*len(headers)
    for j,width in enumerate(widths):tb.columns[j].width=Cm(width)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    tb._tbl.tblPr.append(borders)
    for j,header_text in enumerate(headers):tb.rows[0].cells[j].text=header_text
    for row in rows:
        cells=tb.add_row().cells
        for j,value in enumerate(row):cells[j].text=str(value)
    for i,row in enumerate(tb.rows):
        if i==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
        # A row moves as a unit; content is never clipped by a fixed height.
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        for j,cell in enumerate(row.cells):
            cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props=cell._tc.get_or_add_tcPr();shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'17354C' if i==0 else 'F2F5F8' if i%2==0 else 'FFFFFF');props.append(shade)
            margin=OxmlElement('w:tcMar')
            for edge,value in [('top','70'),('bottom','70'),('left','100'),('right','100')]:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),value);e.set(qn('w:type'),'dxa');margin.append(e)
            props.append(margin)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(2);para.paragraph_format.line_spacing=1.06
                for run in para.runs:
                    run.font.name='Arial';run.font.size=Pt(9)
                    run.font.color.rgb=RGBColor(255,255,255) if i==0 else RGBColor(0,0,0);run.bold=i==0
    p('')
    return tb
def pic(path,width=17):
    if path.exists():
        para=p('');para.add_run().add_picture(str(path),width=Cm(width))
        para.paragraph_format.keep_with_next=True

diagrams()
p('QazCargo жүк тасымалдауды басқару жүйесінің түсіндірмесі','Title')
p('SQL Server және Python Flask негізіндегі 19 кестелі оқу жобасы','Subtitle')
p('Бұл құжат жаңа QazCargo жобасының мақсатын, нақты дерекқор схемасын, Python серверін, әкімші және клиент кабинеттерін түсіндіреді. Жоба жергілікті Windows компьютерінде іске қосылады. Деректер бір SQL Server базасында тұрақты сақталады; сайттың екі бөлімі сол базаға тексерілген API арқылы қосылады.')
p('Құжатпен жұмыс істеу мақсаты — жобаны орнату, негізгі сценарийді көрсету және қорғауда техникалық шешімдерді түсіндіру. Толық бастапқы код жоба папкасында және жеткізілген ZIP ішінде орналасқан.')
table(['Толтырылатын дерек','Мән'],[['Пән','____________________________'],['Топ','____________________________'],['Орындаушы','____________________________'],['Оқытушы','____________________________']],[5,12])
p('Дайындалған күні 18 қазан 2026 жыл')
p('Нұсқа 3   •   Жергілікті оқу жеткізілімі')
doc.add_page_break()
h('Мазмұн')
chapters=['Жобаның мақсаты мен міндеттері','Технологиялар және дерек ағыны','Әкімші мен клиент құқықтары','Дерекқор кестелерінің жіктелуі','Он тоғыз кестенің өрістері','Кестелер арасындағы байланыстар','ER диаграммалар және қалыпқа келтіру','Индекстер және SQL бағдарламалық нысандары','Бизнес ережелері мен уақыт','Экрандар және негізгі сценарийлер','Құжаттар есептер және баспа','Қауіпсіздік шешімдері','Windows орнату және қызмет көрсету','Файлдар картасы','Маңызды кодтың түсіндірмесі','Тестілеу нәтижелері','Қорғау баяндамасы және сұрақ жауап']
for n,title in enumerate(chapters,1):p(f'{n}  {title}')
p('Өрістер бөлімінде әр бағанның типі, NULL рұқсаты, кілті, әдепкі мәні, мақсаты және оқу мысалы берілген. CHECK шарттары кестеден кейін толық келтіріледі. Құжаттағы үлгі тұлғалар, баға және қашықтықтар шынайы коммерциялық дерек ретінде ұсынылмайды.')
doc.add_page_break()
h('1 Жобаның мақсаты мен міндеттері')
p('Жүк тасымалында өтінім, маршрут, көлік, жүргізуші, файл және төлемді бір жерде байланыстыру қажет. QazCargo осы нысандарды бір SQL Server базасына жинап, клиентке өз тасымалын бақылауға, әкімшіге операцияларды басқаруға мүмкіндік береді. Әр тапсырыстың сыртқы нөмірі мен өзгермейтін мәртебе тарихы бар.')
p('Клиент өз атымен тіркеледі, тапсырыс жібереді, құжат жүктейді және қолдауға жазады. Әкімші анықтамалықтарды жүргізеді, өтінімді растайды, рейс жоспарлайды және төлем есебін тіркейді. Негізгі мақсат — оқу кезінде дерекқор байланысын және толық браузер–сервер–SQL жұмысын дәлелдеу.')
p('Нақты банк төлемі, email арқылы пароль қалпына келтіру, интернетке deployment және нейрожелі қызметі негізгі көлемге кірмейді. Қысқа көмек бөлімі — қарапайым ережеге негізделген нұсқаулық. Ол өздігінен деректерді өзгертпейді.')
h('2 Технологиялар және дерек ағыны')
table(['Қабат','Технология','Міндет'],[['Интерфейс','HTML5 CSS3 JavaScript ES modules','Беттер, форма, мәзір, тіл, preview және баспа'],['Сервер','Python Flask және Waitress','HTTP API, сессия, құқық пен бизнес мәндерді тексеру'],['Қосылым','pyodbc және ODBC Driver 18','Параметрленген SQL және транзакция'],['Сақтау','Microsoft SQL Server','19 кесте, FK, CHECK, trigger, procedure және view'],['Басқару','SSMS 22 және VS Code','SQL сұрауын және кодты ашу/түсіндіру']],[3,5,9])
code('Браузер формасы → JavaScript fetch → Flask API\n→ сессия және рөл тексеруі → pyodbc → SQL Server\n→ COMMIT → JSON немесе файл жауабы → жаңартылған экран')
p('SSMS SQL Server-ді басқаруға арналған терезе. Сайт SSMS терезесіне қосылмайды. Windows-тағы SQL Server қызметі мен Python сервері ашық болса, SSMS жабылған кезде де сайт жұмыс істейді. Әкімші мен клиент екі бөлек интерфейс болғанымен, екеуінің сақтайтын базасы біреу — QazCargo.')
p('Ақша SQL-де DECIMAL, Python-да Decimal түрімен есептеледі. JSON ақша мәнін дәл ондық жол ретінде береді. UTC timestamp ISO 8601 +00:00 түрімен келеді; интерфейс оны APP_TIMEZONE аймағында көрсетеді. Браузер localStorage ішінде тек тіл таңдауын сақтайды.')
h('3 Әкімші мен клиент құқықтары')
table(['Әрекет','Әкімші','Клиент'],[['Анықтамалықтар','Клиент/қала/маршрут/тариф/көлік/жүргізушіні басқарады','Таңдауға арналған ашық деректерді оқиды'],['Тапсырыс','Барлық тапсырыс, жүк, рейс және рұқсат етілген мәртебе','Өз өтінімін жасайды; тек өзінің New күйін тоқтатады'],['Төлем','Тіркейді, түзетеді, қате есепті жоя алады','Өз төлемі мен қалдығын оқиды'],['Құжат','Барлығын көреді, тапсырысқа тіркейді','Өз файлын және өз тапсырысына әкімші берген файлды оқиды'],['Құжат жою','Әкімші құқығымен','Тек өзі жүктеген файл'],['Есеп','Тапсырыс, төлем, клиент, автопарк','Өз тапсырысы мен төлемі'],['Аккаунт','Клиентті бұғаттайды/ашады','Өз профилі мен паролін өзгертеді'],['Қолдау','Барлық өтінішке жауап және күй басқару','Өз өтініші мен хаттары']],[3.1,7.1,6.8])
p('Құқық тек мәзірді жасыру арқылы қорғалмайды. Protected decorator әр API сұрауында Users жолын қайта оқып, IsActive, Role және AuthVersion мәндерін тексереді. ClientID сессиядағы UserID арқылы анықталады. Бөтен нөмірді URL-ға қою клиентке басқа тапсырысты ашпайды.')
h('4 Дерекқор кестелерінің жіктелуі')
groups={'OrderDrafts':'Аяқталмаған өтінім','Notifications':'Оқиға хабарламасы','Clients':'Негізгі субъект','Cities':'Анықтамалық','VehicleTypes':'Анықтамалық','Vehicles':'Автопарк','Drivers':'Персонал анықтамалығы','Routes':'Анықтамалық','CargoTypes':'Анықтамалық','Tariffs':'Баға анықтамалығы','Orders':'Негізгі операция','CargoItems':'Операция құрамы','Trips':'Тасымал операциясы','Payments':'Төлем есебі','OrderStatusHistory':'Автоматты тарих','Users':'Аккаунт','Documents':'Файл және метадерек','SupportTickets':'Қолдау өтініші','TicketMessages':'Қолдау хаты'}
table(['Кесте','Мағынасы','Түрі'],[[s['name'],NAMES[s['name']],groups[s['name']]] for s in SCHEMA],[5.3,6.4,5.3])
p('Бастапқы тасымал схемасында 13 кесте бар. Аккаунт, құжат, екі деңгейлі қолдау және хабарландырулар үшін черновиктерді қоса алты кесте қосылғанда жалпы саны 19 болады. Барлық кестеде INT IDENTITY(1,1) бастапқы кілті бар. NULL тек міндетті емес деректе қолданылады.')
h('5 Он тоғыз кестенің өрістері')
p('Төмендегі анықтамалық нақты орнатылған QazCargo базасының sys.columns, sys.foreign_keys, sys.indexes және sys.check_constraints метадеректерінен жасалды. Мысалдар — оқу мәндері. Барлық FK үшін жою және жаңарту саясаты NO ACTION; байланысқан жазба каскадпен жойылмайды.')
dbtext=['QAZCARGO ДЕРЕКҚОР АНЫҚТАМАЛЫҒЫ\n19 кесте, 25 FK. Нақты SQL метадеректері.\n']
for n,s in enumerate(SCHEMA,1):
    name=s['name'];h(f'5.{n} {name} {NAMES[name]}',2)
    intro=p(f'{name} кестесі {NAMES[name].lower()} деректерін сақтайды. Төмендегі NULL бағанындағы «жоқ» мәні өрісті міндетті етеді.');intro.paragraph_format.keep_with_next=True
    rows=[];dbtext.append(f'\n{n}. {name} — {NAMES[name]}')
    for c in s['columns']:
        desc,example=MEANING[c['name']]
        if c['name']=='Status':example={'Orders':'New, Confirmed, InTransit, Delivered, Cancelled','Trips':'Planned, InTransit, Completed, Cancelled','SupportTickets':'Open, InProgress, Closed'}.get(name,example)
        if c['name']=='Name':example={'Cities':'Астана','VehicleTypes':'Тент','CargoTypes':'Жалпы жүк','Tariffs':'Стандарт · оқу үлгісі','Clients':'Оқу клиенті'}.get(name,example)
        rule=keys(s,c)
        rows.append([c['name']+'\n'+sqltype(c),'иә' if c['is_nullable'] else 'жоқ',rule,desc+'\nМысал: '+example])
        dbtext.append(c['name']+' | '+sqltype(c)+' | NULL '+('YES' if c['is_nullable'] else 'NO')+' | '+rule+' | '+desc+' | '+example)
    table(['Өріс және SQL типі','NULL','Кілт және DEFAULT','Мақсаты және оқу мысалы'],rows,[4.0,1.4,4.8,6.8])
    for ck in s['checks']:
        p('CHECK '+ck['definition'])
        dbtext.append('CHECK '+ck['definition'])
    if name=='Users':p('ClientID NULL емес жолдарға filtered UNIQUE индекс қойылған: бір клиентке бір аккаунт. Admin үшін ClientID NULL болады, сондықтан бірнеше әкімші жасауға болады. AuthVersion өскенде бұрынғы cookie нұсқалары қабылданбайды.')
    if name=='Documents':p('Content файлдың нақты байттарын сақтайды. FileSize 1–20971520 аралығында және DATALENGTH(Content)-ке тең болуы тиіс. Тізім сұрауы Content өрісін әдейі оқымайды.')
    if name=='Orders':p('QuotedAmount — тарихи баға. Тариф не маршрут анықтамалығы өзгергенде бұрынғы тапсырыстың бағасы автоматты өзгермейді. Рұқсат етілген жүк/маршрут өзгерісі болғанда SQL қайта есептейді.')
    if name=='CargoItems':p('WeightKg және VolumeM3 позициядағы барлық қаптаманың жалпы мәндері. Quantity — тек қаптамалар саны. Формула WeightKg-ны Quantity-ге қайта көбейтпейді.')
    if name=='Trips':p('OrderID UNIQUE болғандықтан бір тапсырысқа ең көбі бір рейс жолы болады. Confirmed тапсырыстың тоқтатылған рейсін қайта жоспарлағанда осы жол өңделеді.')
(OUT/'DATABASE_GUIDE.txt').write_text('\n'.join(dbtext),encoding='utf-8')
h('6 Кестелер арасындағы байланыстар')
p('Ата-ана кестенің PK мәні бала кестенің FK мәніне сәйкес келеді. 1:N — бір ата-анаға бірнеше бала; 1:0..1 — бір ата-анаға ең көбі бір бала. NULL рұқсаты баланың байланыссыз сақтала алатынын анықтайды. Төмендегі баған бала жағынан міндеттілікті көрсетеді.')
links=[]
for s in SCHEMA:
    for fk in s['foreign_keys']:
        col=next(c for c in s['columns'] if c['name']==fk['column_name'])
        relation='1 : 0..1' if (s['name'],col['name']) in [('Users','ClientID'),('Trips','OrderID')] else '1 : N'
        links.append([fk['referenced_table']+'.'+fk['referenced_column'],s['name']+'.'+col['name'],relation,'міндетті емес' if col['is_nullable'] else 'міндетті'])
table(['PK ата ана','FK бала','Қатынас','Бала үшін'],links,[5.8,6.3,2.2,2.7])
p('Мысал: Астана қаласы Routes.FromCityID бойынша бірнеше бағытта жөнелту қаласы, ал Routes.ToCityID бойынша бірнеше бағытта жеткізу қаласы бола алады. Бұл бір Cities кестесіне екі бөлек байланыс. Orders→Documents және Orders→SupportTickets FK-лері NULL бола алады: файл не жалпы қолдау сұрағы тапсырыссыз сақталады.')
h('7 ER диаграммалар және қалыпқа келтіру')
p('Күрделі схеманы үш көрініске бөлу негізгі нысандарды оқуды жеңілдетеді. Жебе ата-ана кестеден балаға бағытталған. Orders, Users және VehicleTypes көріністерде әдейі қайталанады; Orders соңғы көріністе де екі рет салынған. Әр атау дерекқорда бір ғана кестені білдіреді. FK NULL белгісі байланыстың бала үшін міндетті емес екенін көрсетеді.')
for name,caption in [('er-orders.png','Тапсырыс бағыты тарифі және жүк құрамы'),('er-operations.png','Рейс ресурстары және есеп'),('er-accounts.png','Аккаунт құжат және қолдау')]:
    pic(OUT/'diagrams'/name);p(caption)
p('Бірінші қалыпты формада әр өріс атомдық мән сақтайды; бірнеше жүкті бір мәтінге жинамай, CargoItems жолдарына бөлеміз. Екінші және үшінші қалыпты формаларда атрибуттар тиісті нысанның кілтіне тәуелді: қала атауы Cities-те, тариф коэффициенттері Tariffs-те сақталады. Тапсырысқа қала атауын көшірмей, RouteID арқылы қосамыз.')
p('QuotedAmount — тарихи келісілген есепті сақтау үшін саналы түрде сақталатын есептік мән. Кейінгі тариф өзгерісі бұрынғы қаржылық есепті бұзбауы керек. Төленген сома бөлек snapshot ретінде қайталанбайды: SUM(Payments.Amount) арқылы есептеледі. VIEW бірнеше жүк пен бірнеше төлемді алдымен жеке агрегаттап, JOIN көбейткішінің қате сомасына жол бермейді.')
h('8 Индекстер және SQL бағдарламалық нысандары')
table(['Нысан','Міндеті'],[['fn_OrderQuote','BasePrice + DistanceKm × PricePerKm + SUM(WeightKg) × PricePerKg; жүк жоқ болса 0. Соңғы соманы екі ондыққа дөңгелектейді.'],['usp_RepriceOrder','New/Confirmed, төлемі және белсенді рейсі жоқ тапсырысты транзакцияда қайта есептейді.'],['usp_SetOrderStatus','Тапсырыс күйін ауыстырады; SQL триггері тарих пен рейс күйін сол транзакцияда сәйкестендіреді.'],['v_OrderOverview','Клиент, екі қала, тариф, жүк агрегаты, төлем, қалдық, рейс, көлік пен жүргізушіні біріктіреді.'],['Orders trigger','Рұқсат етілген ауысу, тарихи деректерді қорғау, автоматты тарих және рейс күйін бір транзакцияда өзгерту.'],['CargoItems trigger','Жүк өзгерту құқығы, соңғы жүктен қорғау және бағаны қайта есептеу.'],['Trips trigger','Түр, белсенділік, сыйымдылық, жергілікті алу күні және уақыт қабаттасуын тексеру.'],['Payments trigger','Жиынтық төлемнің баға шегінен аспауын тексеру.'],['Catalog triggers','Қолданылған тариф параметрлерін және белсенді рейстің ресурстарын қорғау.'],['History және TicketMessages triggers','Тарихты өзгерту/жоюды және жабық не бөтен өтінішке хабарлама қосуды тоқтату.']],[5.2,11.8])
p('FK индекстері байланысқан жолды табуды және ата-ананы жою алдындағы тексеруді жылдамдатады. Orders.ClientID клиент кабинетіне, Orders.OrderDate есеп күніне, Payments.PaidAt төлем есебіне қызмет етеді. Trips көлік/жүргізуші және уақыт индекстері қабаттасуды іздеуге арналған. UNIQUE индекстер email, нөмір, қалалар жұбы және бір тапсырысқа бір рейс сияқты бірегейлікті қорғайды.')
p('Барлық write операциясы SERIALIZABLE транзакцияда және QazCargo.ApiWrite қолданбалық құлпымен орындалады. Бұл шағын оқу жобасында бір мезеттегі жазушыларды реттеп, артық төлем мен қос жоспарлауды тоқтатады. SQL триггерлері тікелей SSMS өзгерістерін де тексереді. Үлкен өндірістік жүйеде құлыптау ұсақ ресурстарға бөлініп, жүктеме сынағы қажет болады.')
h('9 Бизнес ережелері мен уақыт')
code('Баға = BasePrice + DistanceKm × PricePerKm\n       + SUM(CargoItems.WeightKg) × PricePerKg\nМысал = 15000 + 1500 × 120 + 100.25 × 15 = 196503.75 ₸')
p('Жаңа тапсырыс пен алғашқы жүк позициялары бір транзакцияда сақталады. Кейінгі позицияда FK не мән қатесі болса, тапсырыстың өзі де, оның тарихы да rollback болады. OrderNumber UUID негізінде жасалып, SQL UNIQUE арқылы бекітіледі. Клиент жіберген баға API-ға қабылданбайды.')
p('Растау үшін жүк, оң баға және белсенді тариф қажет. Жолға шығару үшін Planned рейс, аяқтау үшін InTransit рейс қажет. New/Confirmed күйінен төлем жоқ кезде тоқтатуға болады; Delivered және Cancelled соңғы күйлер. Клиент тек өзінің New тапсырысын тоқтатады.')
p('Жүк, маршрут және тариф өзгерісі тек New/Confirmed, төлемсіз және белсенді рейссіз жағдайда орындалады. Төлемі бар тапсырыс автоматты refund жасамайды. Төлем — әкімшінің есеп жазбасы; қате жазбаны түзету құқығы әкімшіге ғана берілген.')
p('Көлік тарифтегі VehicleTypeID-ге сәйкес және белсенді болуы керек. Жалпы WeightKg CapacityKg шегінен аспайды. Жүргізуші белсенді болуы керек. Көлік не жүргізуші уақыттары қабаттасқан екі тоқтатылмаған рейске тағайындалмайды. Келу шығудан кейін; жөнелтудің жергілікті күні PickupDate күнінен ерте емес.')
p('Мысал: 20 қараша 2026, 00:30 Asia/Qyzylorda енгізілсе, SQL 19 қараша 19:30 UTC сақтайды. Тексеру UTC күнін емес, жергілікті 20 қарашаны PickupDate-пен салыстырады. Күн есебінің шектері де жергілікті тәуліктің басынан келесі тәуліктің басына дейінгі UTC жартылай ашық аралыққа айналады; соңғы күн толық кіреді.')
h('10 Экрандар және негізгі сценарийлер')
p('Басты беттегі калькулятор SQL бағыттары мен белсенді тарифтерін қолданады. Таңдалған бағыт, тариф және салмақ тек ішкі /login → /customer#newOrder жолына query параметрлерімен беріледі. Сыртқы redirect қабылданбайды. Басты экрандағы көрсеткіштер мен суреттер оқу жобасының мазмұнын түсіндіреді; ойдан клиент пікірлері мен нақты байланыс нөмірлері жоқ.')
for name,caption in [('home.jpg','Нақты басты бет және SQL бағыттары бар калькулятор'),('customer-order.jpg','Сынақ SQL базасында клиент жасаған тапсырыстың нақты карточкасы'),('admin.jpg','Нақты әкімші панелі сынақ деректерімен')]:
    path=OUT/'screenshots'/name
    if path.exists():pic(path);p(caption)
p('Негізгі көрсету сценарийі: клиент өтінім жасайды, әкімші оны растайды, рейс жоспарлап төлем тіркейді, клиент жаңарту арқылы күй мен қалдықты көреді. Шолу және тапсырыс тізімі шамамен 30 секунд сайын автоматты жаңарады; ашық диалог не белсенді толтырылып жатқан форма қайта салынбайды. Жаңа өтінімнің таңдауларын жеке жаңарту батырмасы мәндерді сақтай отырып толықтырады.')
p('Әкімші мәзірінде ашылып-жиналатын төрт топ бар. Клиент мәзірі шолу, тапсырыс, жаңа өтінім, құжат, есеп, қолдау және профильден тұрады. Әрекет мәзірлері Escape және сыртқа шерту арқылы жабылады. Диалогтар пернетақта фокусын ұстайды. Тар экранда бүйір мәзір жиналып, кестелер көлденең айналдырылады.')
h('11 Құжаттар есептер және баспа')
p('Файл жүктеу multipart сұрауы арқылы өтеді; CSRF және иелік тексеруі сол сұрауға да қолданылады. PDF, DOC/DOCX, TXT, JPG/JPEG, PNG, GIF, WEBP, BMP, XLS/XLSX және PPT/PPTX қолдау табады. Бір файлдың шегі 20 МБ. TXT мәтінін сайтта жазып, файл ретінде сол SQL кестесіне сақтауға болады.')
table(['Файл түрі','Көру және басу','Шектеу'],[['PDF','Браузер PDF қарауышы мен оның print функциясы','Белсенді/шифрланған не тым күрделі файл қабылданбайды'],['Сурет TXT','Сайт preview және browser print','Растр өлшемі және мәтін preview көлемі шектелген'],['DOCX','Қарапайым мәтін, кесте, кірістірілген растр','Word беттелуі дәл қайталанбайды; дәл баспаға түпнұсқа қажет'],['DOC XLS XLSX PPT PPTX','Сақтау және түпнұсқаны жүктеу','Дәл көру/басу тиісті Office бағдарламасында']],[3.7,6.5,6.8])
p('DOCX preview сыртқы суреттерді интернеттен алмайды. XML entity, zip bomb, макрос, ActiveX және кірістірілген орындалатын нысандар қабылданбайды. Қолданушы мәтіні HTML ретінде орындалмайды: HTML таңбалары escape жасалады. Қауіпсіз түр тексеруі антивирус сканерінің орнына ұсынылмайды; бұл жеткізілімде бөлек антивирус сервисі жоқ.')
p('Әкімші есептері: тапсырыс, төлем, клиент және автопарк. Клиент тек өз тапсырыс/төлем есебін алады. Тапсырыс OrderDate пен күйге, төлем PaidAt күндеріне сүзіледі. Клиент пен автопаркке қатысы жоқ күн сүзгісі өшіріледі. Сүзгі өзгергенде ескі есеп жасырылып, жаңасын қалыптастыру сұралады.')
p('CSV UTF-8 BOM арқылы Excel-де қазақша мәтінді сақтайды. Формулаға ұқсас ұяшықтар алдына апостроф қойылады. Баспа барлық сүзілген жолды және сомаларды қамтиды. A4 тік/көлденең таңдау, қайталанатын кесте тақырыбы және сурет/қаріп жүктелуін күту бар. Физикалық принтерді үнсіз басқару жоқ; стандартты диалогта принтер немесе Save as PDF таңдалады.')
h('12 Қауіпсіздік шешімдері')
p('Бірінші әкімші тек жергілікті консольден жасалады. Тіркелу сұрауы Role не ClientID өрісін қабылдамайды және тек client жасайды. Құпиясөз scrypt арқылы salt-пен хештеледі. Ашық пароль SQL-де, логта немесе жеткізілген ZIP-те болмайды. APP_SECRET орнатқышта кездейсоқ жасалады және тұрақты .env ішінде сақталады.')
p('Cookie HttpOnly, SameSite=Lax және сегіз сағат мерзімін қолданады. HTTPS production режимінде Secure қосылады. Пароль ауысуы мен аккаунт бұғатталуы AuthVersion мәнін өсіреді. Әр protected сұрау оны SQL-ден тексергендіктен ескі сессиялар жарамсыз болады. Бес қате кіруден кейін он минут шектеу қойылады; қате санағы HTTP қатесінен бұрын commit болады.')
p('Барлық дерек өзгертетін сұрау CSRF токенін және origin мәнін тексереді. SQL мәндері ? параметрімен беріледі. Кесте/өріс атаулары backend/schema.py allowlist-інен алынады. API қате жауабы тек аударылатын код пен өрісті қайтарады; traceback, пароль, connection string клиентке шықпайды. CSP, nosniff және no-store тақырыптары қосымша қорғаныс береді.')
h('13 Windows орнату және қызмет көрсету')
p('Осы компьютерде localhost SQL Server қосылымы тексеріліп, QazCargo базасы жаңадан құрылды. QazCargo13 сақталды. Жұмыс базасына тек оқу анықтамалықтары енгізілді. Әкімшіге дайын ортақ пароль тағайындалмайды: SET_ADMIN.bat ашып, өз email, аты-жөні және 10–128 таңбалы парольді екі рет енгізіңіз. Жаңа компьютерде ZIP-ті толық шығарып, FIRST_RUN.bat қолданыңыз.')
code('PowerShell\ncd "C:\\Projects\\QazCargo"\n.\\FIRST_RUN.bat      # тек алғашқы орнату\n.\\SET_ADMIN.bat      # әкімші жасау не қалпына келтіру\n.\\START.bat          # күнделікті іске қосу')
p('VS Code → File → Open Folder арқылы QazCargo папкасын ашыңыз немесе QazCargo.code-workspace таңдаңыз. Толық Visual Studio үшін QazCargo.sln және Python development workload керек. Осы ортада VS Code іске қосылды; толық Visual Studio IDE debug бөлек тексерілмеген. SSMS-тағы Server name мәнін .env ішіндегі DB_SERVER-мен сәйкестендіріңіз.')
code('py -3 -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.\\.venv\\Scripts\\python.exe -m backend.install\n.\\.venv\\Scripts\\python.exe -m backend.app')
p('SQL файлдарын қолмен орнату: SSMS-та 01_create_database.sql ашып F5, қате болмаса 02_seed_catalogs.sql. Орнатқыш бұрын орындаса, оларды қайталамаңыз. Тексеру үшін 03_verify.sql жеткілікті. Браузер адресі http://127.0.0.1:5000; әкімші /admin, клиент /customer. Екі рөлді көрсету үшін инкогнито пайдаланыңыз.')
p('Терминал сервер жұмыс істегенде ашық қалады. Ctrl+C тоқтатады; batch сұраса Y → Enter. SQL жазбалары сақталады. Келесі күні FIRST_RUN емес, START қолданыңыз. HTML/CSS/JS үшін Ctrl+S және Ctrl+F5; Python өзгерсе серверді қайта іске қосыңыз. Go Live Python API-ды іске қоспайды.')
p('BACKUP.bat COPY_ONLY және CHECKSUM резервін жасайды, кейін RESTORE VERIFYONLY WITH CHECKSUM тексереді. Жол BACKUP_LOCATIONS.txt ішінде жазылады. Reset тек дәл QazCargo атауын енгізгенде, тексерілген резервтен соң орындалады. Қате болса DROP орындалмайды және MULTI_USER қалпына келеді. VERIFYONLY нақты restore сынағын алмастырмайды. Қалпына келтіруді алдымен бөлек базаға сынау ұсынылады.')
table(['Мәселе','Тексеру'],[['Python не py жоқ','Python launcher орнатылсын; жаңа терминал ашыңыз.'],['ODBC/pyodbc жоқ','ODBC Driver 18 x64 және requirements.txt орнатыңыз.'],['SQL қосылым қатесі','SQL қызметі Running, SSMS Server name, Windows Authentication рұқсаты және .env.'],['Сертификат','Жергілікті TrustServerCertificate=yes; production үшін сенімді TLS.'],['5000 бос емес','Осы жобаның бұрынғы серверін Ctrl+C арқылы тоқтатыңыз.'],['Backup құқық қатесі','SQL Server қызмет аккаунтының backup папкасына жазу құқығын тексеріңіз.'],['Кіру шектеуі','10 минут күту; әкімшіге жергілікті SET_ADMIN.bat.'],['Файл қатесі','Көлем, пішім, сигнатура, шифр және макростарды тексеріңіз.']],[5,12])
h('14 Файлдар картасы')
table(['Файл','Міндеті'],[[k,v] for k,v in FILES.items()],[6.1,10.9])
(OUT/'PROJECT_GUIDE.txt').write_text('QAZCARGO ЖОБА КАРТАСЫ\n\n'+'\n\n'.join(k+'\n'+v for k,v in FILES.items()),encoding='utf-8')
h('15 Маңызды кодтың түсіндірмесі')
code("with transaction(write=True) as q:\n    order = own_order(q, user, order_id)\n    q.execute(\n        'EXEC dbo.usp_SetOrderStatus @OrderID=?,@NewStatus=?',\n        (order_id, target_status))")
p('Transaction контексті connection ашып, жазу құлпын алады. Әрекет сәтті болса commit, exception болса rollback, соңында connection жабылады. own_order клиентке тек өзінің тапсырысын береді. Екі ? белгісі параметр орны; қолданушы мәні SQL мәтініне жапсырылмайды.')
code("total = (base + distance * per_km + weight * per_kg)\namount = total.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)")
p('Бұл формулада барлық operand Decimal. Қаптама саны салмаққа қайта көбейтілмейді. Public калькулятор алдын ала бағалайды, ал SQL триггері сақталатын QuotedAmount мәнін қайта есептейді. Екі қабат бір формуланы қолданады.')
code('SELECT o.OrderNumber, c.Name, f.Name AS FromCity, t.Name AS ToCity\nFROM dbo.Orders o\nJOIN dbo.Clients c ON c.ClientID=o.ClientID\nJOIN dbo.Routes r ON r.RouteID=o.RouteID\nJOIN dbo.Cities f ON f.CityID=r.FromCityID\nJOIN dbo.Cities t ON t.CityID=r.ToCityID;')
p('Cities кестесі f және t бүркеншік атауларымен екі рет қосылады: біреуі жөнелту, екіншісі жеткізу қаласы. Бұл бағыт дерегін атаумен қайталап сақтамай, нормаланған кілт арқылы алуға мүмкіндік береді. Толық тексеру сұраулары 03_verify.sql ішінде.')
h('16 Тестілеу нәтижелері')
validation=(ROOT/'VALIDATION.txt').read_text(encoding='utf-8-sig') if (ROOT/'VALIDATION.txt').exists() else 'Бастапқы тексеру: 31 Python тесті нақты SQL Server және installer unit деңгейінде өтті. Соңғы есеп VALIDATION.txt ішінде жаңартылады.'
for paragraph in validation.split('\n\n'):
    if paragraph.strip():p(paragraph.strip())
p('Автоматты SQL сынақтары QazCargo_Test_... уақытша базасында орындалады. Операциялар нақты SQL Server-де орындалды. Браузердің сынақ экраны QazCargo_UI_... базасындағы уақытша деректерді пайдаланды; олар жұмыс QazCargo базасының шынайы клиенттері емес. Тест деректері дайын жұмыс базасына үнсіз көшірілмейді.')
h('17 Қорғау баяндамасы және сұрақ жауап')
defense=(OUT/'DEFENSE_KZ.txt').read_text(encoding='utf-8-sig')
for para in defense.split('\n\n')[1:]:p(para)
h('Пайдаланылған техникалық дереккөздер',2)
p('Flask қауіпсіздік және cookie құжаттамасы: https://flask.palletsprojects.com/en/stable/web-security/')
p('SQL Server көп жолды DML триггерлері: https://learn.microsoft.com/en-us/sql/relational-databases/triggers/create-dml-triggers-to-handle-multiple-rows-of-data')
p('Негізгі талап көзі — пайдаланушы берген QazCargo_Codex_Full_Prompt.txt. Бұрынғы ZIP үлгі ретінде оқылды. Жаңа Python және интерфейс модульдері жазылды; талаппен сәйкес SQL DDL мен жүк көлігі суреті үлгіден алынып, SQL уақыт/тұтастық ережелері, VIEW және индекстері жаңартылды.')
path=OUT/'QazCargo_Tusindirme.docx';doc.save(path)
print('Created',path,'with',len(SCHEMA),'table dictionaries',flush=True)
