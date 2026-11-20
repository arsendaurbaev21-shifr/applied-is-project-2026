"""Labs 1–7: Streamlit forms and tables communicating with FastAPI over HTTP."""
from datetime import date, timedelta
import os
import streamlit as st
from labs.lab_1_2.ui_client import ApiClient, ApiError

STATUS = {"New": "Жаңа", "Confirmed": "Расталды", "InTransit": "Жолда",
          "Delivered": "Жеткізілді", "Cancelled": "Бас тартылды"}
PAGES = ["Тапсырыстар", "Жаңа тапсырыс", "Өзгерту және өшіру", "Жоба туралы"]


def choose(label, rows, key):
    names = {row["id"]: row["name"] for row in rows}
    return st.selectbox(label, list(names), format_func=names.get, key=key)


def return_to_orders(message, search=""):
    st.session_state["flash"] = message
    st.session_state["goto_page"] = PAGES[0]
    st.session_state["next_search"] = search
    st.rerun()


def order_list(api):
    st.subheader("Тасымалдау тапсырыстары")
    search = st.text_input("Нөмір немесе клиент бойынша іздеу", key="search", max_chars=120)
    left, right, state_column = st.columns(3)
    with left:
        use_min = st.checkbox("Ең төменгі баға", key="use_min")
        minimum = st.number_input("Бастапқы баға, ₸", min_value=0.0, value=0.0, step=1000.0,
                                  max_value=999999999999.99, disabled=not use_min, key="min_price")
    with right:
        use_max = st.checkbox("Ең жоғарғы баға", key="use_max")
        maximum = st.number_input("Соңғы баға, ₸", min_value=0.0, value=200000.0, step=1000.0,
                                  max_value=999999999999.99, disabled=not use_max, key="max_price")
    with state_column:
        status = st.selectbox("Мәртебе", ["", *STATUS], format_func=lambda value: STATUS.get(value, "Барлығы"), key="status")
        size = st.selectbox("Бір беттегі саны", [20, 50, 100], key="page_size")
    if use_min and use_max and minimum > maximum:
        st.error("Бастапқы баға соңғы бағадан үлкен болмауы тиіс.")
        return
    params = {"search": search.strip()}
    if use_min:
        params["min_price"] = f"{minimum:.2f}"
    if use_max:
        params["max_price"] = f"{maximum:.2f}"
    if status:
        params["status"] = status
    signature = (tuple(sorted(params.items())), size)
    if st.session_state.get("filters") != signature:
        st.session_state.update(filters=signature, page_index=0)
    page = st.session_state.get("page_index", 0)
    rows = api.request("GET", "/api/orders", params={**params, "offset": page * size, "limit": size + 1})
    has_next = len(rows) > size
    rows = rows[:size]
    if rows:
        st.dataframe([{"ID": row["id"], "Нөмір": row["number"], "Клиент": row["client"],
                       "Бағыт": row["route"], "Бағасы, ₸": row["quoted_amount"],
                       "Мәртебе": STATUS[row["status"]], "Ескерту": row["notes"] or ""}
                      for row in rows], hide_index=True, width="stretch")
        selected = st.selectbox("Жүк құрамын көру", rows, format_func=lambda row: row["number"], key="detail")
        st.dataframe([{"Жүк түрі": item["type"], "Сипаттама": item["description"],
                       "Салмақ, кг": item["weight_kg"], "Көлем, м³": item["volume_m3"], "Саны": item["quantity"]}
                      for item in selected["items"]], hide_index=True, width="stretch")
    else:
        st.info("Осы шарттарға сәйкес тапсырыс табылмады. Іздеу мен баға сүзгісін өзгертіңіз.")
    previous, current, following = st.columns([1, 2, 1])
    if previous.button("← Алдыңғы бет", disabled=page == 0, key="previous"):
        st.session_state["page_index"] = page - 1
        st.rerun()
    current.caption(f"{page + 1}-бет · көрсетілген тапсырыстар: {len(rows)}")
    if following.button("Келесі бет →", disabled=not has_next, key="next"):
        st.session_state["page_index"] = page + 1
        st.rerun()


def create_form(api):
    st.subheader("Жаңа тасымалдау тапсырысы")
    catalogs = api.request("GET", "/api/catalogs")
    catalogs["tariffs"] = [row for row in catalogs["tariffs"] if row["active"]]
    if not all(catalogs.values()):
        st.warning("Тапсырыс жасауға қажет анықтамалықтар бос. Оқу базасын дайындаңыз.")
        return
    count = st.number_input("Жүк позицияларының саны", min_value=1, max_value=10, value=1, step=1, key="item_count")
    revision = st.session_state.get("create_revision", 0)
    prefix = f"new_{revision}"
    with st.form("new_order_form"):
        client = choose("Клиент", catalogs["clients"], prefix + "_client")
        route = choose("Бағыт", catalogs["routes"], prefix + "_route")
        tariff = choose("Тариф", catalogs["tariffs"], prefix + "_tariff")
        pickup = st.date_input("Жүкті алып кету күні", value=date.today() + timedelta(days=1), key=prefix + "_date")
        notes = st.text_area("Ескерту", max_chars=500, key=prefix + "_notes")
        items = []
        for index in range(count):
            key = f"{prefix}_{index}"
            st.markdown(f"**{index + 1}-жүк позициясы**")
            cargo_type = choose("Жүк түрі", catalogs["cargo_types"], key + "_type")
            description = st.text_input("Жүктің сипаттамасы", max_chars=200, key=key + "_description")
            a, b, c = st.columns(3)
            weight = a.number_input("Жалпы салмақ, кг", min_value=0.01, max_value=9999999999.99,
                                    value=10.0, step=0.01, format="%.2f", key=key + "_weight")
            volume = b.number_input("Жалпы көлем, м³", min_value=0.001, max_value=999999999.999,
                                    value=0.5, step=0.001, format="%.3f", key=key + "_volume")
            quantity = c.number_input("Саны", min_value=1, max_value=2147483647, value=1, step=1, key=key + "_quantity")
            items.append({"cargo_type_id": cargo_type, "description": description.strip(),
                          "weight_kg": f"{weight:.2f}", "volume_m3": f"{volume:.3f}", "quantity": quantity})
        st.caption("Салмақ пен көлем — позицияның жалпы мәндері. Бағаны жүйе тариф бойынша есептейді.")
        submitted = st.form_submit_button("Тапсырысты сақтау", type="primary")
    if submitted:
        if any(not item["description"] for item in items):
            st.warning("Әр жүк позициясының сипаттамасын толтырыңыз.")
            return
        created = api.request("POST", "/api/orders", json={"client_id": client, "route_id": route,
                              "tariff_id": tariff, "pickup_date": pickup.isoformat(),
                              "notes": notes.strip() or None, "items": items})
        st.session_state["create_revision"] = revision + 1
        return_to_orders(f"{created['number']} тапсырысы сақталды. Бағасы: {created['quoted_amount']} ₸.", created["number"])


def edit_form(api):
    st.subheader("Тапсырысты өзгерту және өшіру")
    search = st.text_input("Өзгертілетін тапсырысты іздеу", max_chars=120, key="edit_search")
    rows = api.request("GET", "/api/orders", params={"search": search.strip(), "limit": 200})
    if not rows:
        st.info("Тапсырыс табылмады.")
        return
    names = {row["id"]: f"{row['number']} · {row['client']}" for row in rows}
    ident = st.selectbox("Тапсырысты таңдаңыз", list(names), index=None, format_func=names.get,
                         placeholder="Нөмірін таңдаңыз", key="edit_order")
    if ident is None:
        return
    order = api.request("GET", f"/api/orders/{ident}")
    st.caption(f"{order['route']} · {STATUS[order['status']]} · {order['quoted_amount']} ₸")
    if order["status"] != "New":
        st.info("Тек «Жаңа» күйіндегі тапсырысты өзгертуге немесе өшіруге болады.")
        return
    with st.form(f"edit_{ident}"):
        notes = st.text_area("Жаңа ескерту", value=order["notes"] or "", max_chars=500, key=f"notes_{ident}")
        st.caption("Ескерту бос болса, бұрынғы мәтін тазартылады. Басқа өрістер өзгермейді.")
        save = st.form_submit_button("Ескертуді сақтау", type="primary")
    if save:
        api.request("PATCH", f"/api/orders/{ident}", json={"notes": notes.strip() or None})
        return_to_orders("Тапсырыстың ескертуі жаңартылды.", order["number"])
    with st.form(f"delete_{ident}"):
        confirmed = st.checkbox(f"{order['number']} тапсырысы мен жүк позицияларын өшіруді растаймын", key=f"confirm_{ident}")
        remove = st.form_submit_button("Тапсырысты өшіру")
    if remove:
        if not confirmed:
            st.warning("Өшіру үшін растау белгісін қойыңыз.")
            return
        api.request("DELETE", f"/api/orders/{ident}")
        return_to_orders(f"{order['number']} тапсырысы өшірілді.")


def main():
    st.set_page_config(page_title="QazCargo зертханасы", page_icon="🚚", layout="wide")
    st.title("QazCargo · Жүк тасымалдау")
    st.caption("Даурбаев Арсен · ИС-24А · Зертханалық жұмыстар 1–7")
    if "goto_page" in st.session_state:
        st.session_state["page"] = st.session_state.pop("goto_page")
        st.session_state["search"] = st.session_state.pop("next_search", "")
        st.session_state.update(use_min=False, use_max=False, status="", page_index=0)
    with st.sidebar:
        st.header("Басқару")
        page = st.radio("Бөлім", PAGES, key="page")
        if st.button("Деректерді жаңарту", key="refresh"):
            st.rerun()
        st.caption("Оқу базасындағы жасанды деректер. Негізгі Cargo сайтының деректері бөлек сақталады.")
        st.link_button("Swagger API", os.getenv("PUBLIC_API_URL", "http://localhost:8000/docs"))
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
    if page == PAGES[3]:
        st.subheader("Жоба туралы")
        st.write("QazCargo клиенттердің жүк тасымалдау тапсырыстарын, бағыттарын, тарифтерін және жүк құрамын есепке алады.")
        st.write("Бұл оқу модулінде тапсырыстарды көруге, іздеуге, жасауға, ескертуді өзгертуге және өшіруге болады.")
        return
    api = ApiClient()
    try:
        summary = api.request("GET", "/api/summary")
        for column, (label, table) in zip(st.columns(4), (("Клиенттер", "Clients"), ("Тапсырыстар", "Orders"),
                                                          ("Жүк түрлері", "CargoTypes"), ("Жүк позициялары", "CargoItems"))):
            column.metric(label, summary["tables"][table])
        {PAGES[0]: order_list, PAGES[1]: create_form, PAGES[2]: edit_form}[page](api)
    except ApiError as error:
        st.error(str(error))


main()
