"""Run from QazCargo root: python -m streamlit run labs/lab_1_2/frontend.py."""
import json
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
import streamlit as st

st.set_page_config(page_title="QazCargo зертханасы", page_icon="🚚", layout="wide")
st.title("QazCargo зертханалық модулі")
st.caption("Даурбаев Арсен · ИС-24А · Зертханалық жұмыстар 1–4")
st.info("Бұл бет бөлек оқу базасындағы жасанды деректерді көрсетеді.")


def api(path):
    with urlopen("http://127.0.0.1:8000/api/" + path, timeout=5) as response:
        return json.load(response)


if st.button("Деректерді жаңарту"):
    st.rerun()
try:
    summary, orders = api("summary"), api("orders")
except (URLError, HTTPError, TimeoutError, OSError, ValueError):
    st.warning("FastAPI іске қосылмаған. Алдымен LAB_API.bat файлын ашыңыз.")
    st.stop()

columns = st.columns(4)
for column, (label, table) in zip(columns, (("Клиенттер", "Clients"), ("Тапсырыстар", "Orders"), ("Жүк түрлері", "CargoTypes"), ("Жүк позициялары", "CargoItems"))):
    column.metric(label, summary["tables"][table])
if not orders:
    st.warning("База бос. LAB_SETUP.bat арқылы оқу деректерін толтырыңыз.")
else:
    st.subheader("Тасымалдау тапсырыстары")
    st.dataframe([{"Нөмір": o["number"], "Клиент": o["client"], "Бағыт": o["route"],
                   "Жүк түрлері": ", ".join(o["cargo_types"]), "Бағасы, ₸": o["quoted_amount"],
                   "Мәртебе": o["status"]} for o in orders], hide_index=True)
    selected = st.selectbox("Тапсырыстың жүк құрамы", orders, format_func=lambda o: o["number"])
    st.dataframe(selected["items"], hide_index=True)
st.link_button("API құжаттамасы", "http://127.0.0.1:8000/docs")
