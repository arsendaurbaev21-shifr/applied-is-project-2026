from pathlib import Path
import requests
from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[1] / 'labs/lab_1_2/frontend.py'


def screen():
    result = AppTest.from_file(str(FRONTEND)).run(timeout=30)
    assert not result.exception
    return result


def submit(app, label):
    next(button for button in app.button if button.label == label).click().run(timeout=30)
    assert not app.exception
    return app


def test_search_and_price_filters_use_live_api(ui_backend):
    app = screen()
    assert [metric.value for metric in app.metric] == ['3', '3', '3', '5']
    assert len(app.dataframe[0].value) == 3
    app.text_input(key='search').set_value('LAB-2026-002').run()
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]['Нөмір'] == 'LAB-2026-002'
    app.text_input(key='search').set_value('no-such-order').run()
    assert not app.dataframe
    assert app.info
    app.text_input(key='search').set_value('').run()
    app.checkbox(key='use_min').check().run()
    app.number_input(key='min_price').set_value(1.0).run()
    assert not app.dataframe  # Historical seed prices are zero.


def test_create_form_adds_two_positions_and_refreshes_list(ui_backend):
    app = screen()
    app.sidebar.radio(key='page').set_value('Жаңа тапсырыс').run()
    app.number_input(key='item_count').set_value(2).run()
    app.text_input(key='new_0_0_description').set_value('Бірінші жүк')
    app.text_input(key='new_0_1_description').set_value('Екінші жүк')
    submit(app, 'Тапсырысты сақтау')
    assert app.success
    assert app.sidebar.radio(key='page').value == 'Тапсырыстар'
    assert len(app.dataframe[0].value) == 1
    number = app.dataframe[0].value.iloc[0]['Нөмір']
    order = ui_backend.get('/api/orders', params={'search': number}).json()[0]
    assert len(order['items']) == 2
    assert order['quoted_amount'] == '165300.00'


def test_empty_description_keeps_form_and_database(ui_backend):
    app = screen()
    app.sidebar.radio(key='page').set_value('Жаңа тапсырыс').run()
    submit(app, 'Тапсырысты сақтау')
    assert app.warning
    assert app.sidebar.radio(key='page').value == 'Жаңа тапсырыс'
    assert len(ui_backend.get('/api/orders').json()) == 3


def test_patch_then_confirmed_delete(ui_backend):
    app = screen()
    app.sidebar.radio(key='page').set_value('Өзгерту және өшіру').run()
    app.selectbox(key='edit_order').set_value(1).run()
    app.text_area(key='notes_1').set_value('Жаңартылған ескерту')
    submit(app, 'Ескертуді сақтау')
    assert ui_backend.get('/api/orders/1').json()['notes'] == 'Жаңартылған ескерту'
    app.sidebar.radio(key='page').set_value('Өзгерту және өшіру').run()
    app.selectbox(key='edit_order').set_value(1).run()
    submit(app, 'Тапсырысты өшіру')
    assert app.warning
    assert ui_backend.get('/api/orders/1').status_code == 200
    app.checkbox(key='confirm_1').check()
    submit(app, 'Тапсырысты өшіру')
    assert app.success
    assert ui_backend.get('/api/orders/1').status_code == 404
    assert len(app.dataframe[0].value) == 2


def test_bad_price_range_is_explained(ui_backend):
    app = screen()
    app.checkbox(key='use_min').check().run()
    app.checkbox(key='use_max').check().run()
    app.number_input(key='min_price').set_value(300000.0).run()
    assert app.error
    assert not app.exception


def test_disconnected_backend_shows_error_without_crashing(monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, 'request', offline)
    app = screen()
    assert app.error
    assert not app.exception
