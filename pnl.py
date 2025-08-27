import os
import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder, AgGrid, JsCode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(BASE_DIR, "base.xlsx")  # <- ahora lee desde la raíz

# --- reglas de expansión ---
NO_EXPAND_N0 = {"Ventas","Margen","Contribucion","Administracion Central","Royaltie","Resultado Operativo","Impuesto a la Renta","Diferencia Cambiaria","Resultado Neto",
                "Flujo","Ventas","EBITAD"}                         # nunca se expande (nivel 0)
ONE_LEVEL_N0 = {"Costo","Marketing","Alquiler", "Mantenimiento","Depresiacion","Extraordinario Cash","Extraordinario No Cash"}        # solo un nivel (n0 -> n1)
N2_ALLOWED_FOR_N1 = {                               # n1 que sí puede abrir n2
    ("Gastos Operativos", "Gastos Generales"),
    ("Gastos Operativos", "Gastos Personal"),
}

# --- Estilos globales para celdas (usados en _grid_format) ---
totalizer_cellstyle = JsCode("""
function(params){
    var d = params.data || {};
    var cta = (d.Cuenta || '').toString().trim().toLowerCase();
    var isTotal = (d.Nodo === 'n0') && (
        cta === 'ventas' ||
        cta === 'margen' ||
        cta === 'contribucion' ||
        cta === 'resultado operativo' ||
        cta === 'resultado neto' ||
        cta === 'flujo'
    );
    var style = {};
    if (isTotal){
        style.backgroundColor = '#d7ffd9';
        style.fontWeight = '700';
    }
    var v = params.value;
    if (v !== null && v !== undefined && !isNaN(v) && Number(v) < 0){
        style.color = 'red';
    }
    return style;
}
""")

cuenta_cellstyle = JsCode("""
function(params){
    var d = params.data || {};
    var style = {};
    if (d && (d.nivel === 0 || d.nivel === 1)){ style.cursor = 'pointer'; }
    var cta = (d.Cuenta || '').toString().trim().toLowerCase();
    var isTotal = (d.Nodo === 'n0') && (
        cta === 'ventas' ||
        cta === 'margen' ||
        cta === 'contribucion' ||
        cta === 'resultado operativo' ||
        cta === 'resultado neto' ||
        cta === 'flujo'
    );
    if (isTotal){
        style.backgroundColor = '#d7ffd9';
        style.fontWeight = '700';
    }
    return style;
}
""")

# ---------- utils ----------
def rerun_app():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except Exception:
            pass

def _third_level_col(df: pd.DataFrame):
    candidatos = ["Linea", "Tipo", "Detalle", "SubSubCuenta"]
    for c in candidatos:
        if c in df.columns:
            if df[c].astype(str).str.strip().ne("").any():
                return c
    return None

def _sub_from_display(val: str) -> str:
    if val is None:
        return ""
    t = str(val)
    t = t.replace("•", "").replace("·", "").strip()
    if t.startswith("- "):
        t = t[2:].strip()
    return t

def _norm(s: str) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()

@st.cache_data
def cargar_datos(path: str, mtime: float):
    try:
        df = pd.read_excel(path, sheet_name="datos")
    except ValueError:
        df = pd.read_excel(path)  # fallback a primera hoja

    for col in ["ACT", "AA", "PPTO"]:
        if df.get(col) is not None and df[col].dtype == "object":
            df[col] = (
                df[col].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for c in ["Cuentas", "SubCuenta", "Tipo"]:
        if c not in df.columns:
            df[c] = ""

    df["Cuentas"]   = df["Cuentas"].fillna("").astype(str)
    df["SubCuenta"] = df["SubCuenta"].fillna("").astype(str)
    return df

def _checklist_filter(label: str, options, key_prefix: str):
    import streamlit as st
    opts = [str(o) for o in options]

    state_key    = f"{key_prefix}_selected"
    snapshot_key = f"{key_prefix}_snapshot"

    if (state_key not in st.session_state) or (snapshot_key not in st.session_state) \
       or (st.session_state[snapshot_key] != tuple(options)):
        st.session_state[state_key] = set(opts)
        st.session_state[snapshot_key] = tuple(options)

    title = f"{label}  ({len(st.session_state[state_key])}/{len(opts)})"

    # popover si existe; si no, expander (compatible con 1.31.1)
    if hasattr(st, "popover"):
        container = st.popover(title, use_container_width=True)
    else:
        container = st.expander(title, expanded=False)

    with container:
        all_selected_now = len(st.session_state[state_key]) == len(opts)
        sel_all = st.checkbox("Seleccionar todo", value=all_selected_now, key=f"{key_prefix}_all")
        if sel_all:
            st.session_state[state_key] = set(opts)

        st.markdown("---")

        changed = False
        new_selected = set(st.session_state[state_key])
        for o in opts:
            ck = st.checkbox(o, value=(o in st.session_state[state_key]), key=f"{key_prefix}_{o}")
            if ck and o not in new_selected:
                new_selected.add(o); changed = True
            elif (not ck) and (o in new_selected):
                new_selected.discard(o); changed = True

        if changed or (sel_all and not all_selected_now):
            st.session_state[state_key] = new_selected
            st.session_state["_filters_nonce"] = st.session_state.get("_filters_nonce", 0) + 1

    return [o for o in options if str(o) in st.session_state[state_key]]

def _layout_filtros(df):
    col1, col2, col3, col4 = st.columns(4)
    anios      = sorted(df["Anual"].dropna().unique().tolist())       if "Anual"    in df.columns else []
    periodos   = sorted(df["Periodo"].dropna().unique().tolist())     if "Periodo"  in df.columns else []
    orden_meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    if "Fecha" in df.columns:
        meses_unicos = df["Fecha"].dropna().unique().tolist()
        meses = [m for m in orden_meses if m in meses_unicos]
    else:
        meses = []
    sucursales = sorted(df["Sucursal"].dropna().unique().tolist())    if "Sucursal" in df.columns else []

    with col1: anio_sel     = _checklist_filter("Año",     anios,     "anio")
    with col2: periodo_sel  = _checklist_filter("Periodo", periodos,  "periodo")
    with col3: mes_sel      = _checklist_filter("Mes",     meses,     "mes")
    with col4: sucursal_sel = _checklist_filter("Sucursal",sucursales,"sucursal")
    return anio_sel, periodo_sel, mes_sel, sucursal_sel

def _aplicar_filtros(df, anios_sel, periodos_sel, meses_sel, sucursales_sel):
    df_f = df.copy()
    if "Anual" in df_f.columns and anios_sel is not None:
        if len(anios_sel) > 0 and len(anios_sel) != df_f["Anual"].nunique():
            df_f = df_f[df_f["Anual"].isin(anios_sel)]
    if "Periodo" in df_f.columns and periodos_sel is not None:
        if len(periodos_sel) > 0 and len(periodos_sel) != df_f["Periodo"].nunique():
            df_f = df_f[df_f["Periodo"].isin(periodos_sel)]
    if "Fecha" in df_f.columns and meses_sel is not None:
        if len(meses_sel) > 0 and len(meses_sel) != df_f["Fecha"].nunique():
            df_f = df_f[df_f["Fecha"].isin(meses_sel)]
    if "Sucursal" in df_f.columns and sucursales_sel is not None:
        if len(sucursales_sel) > 0 and len(sucursales_sel) != df_f["Sucursal"].nunique():
            df_f = df_f[df_f["Sucursal"].isin(sucursales_sel)]
    return df_f

def _calc(df_sum, total_act, total_aa, total_ppto):
    df = df_sum.copy()
    df["pct_act"]  = df["ACT"] / (total_act if total_act else 1)
    df["pct_aa"]   = df["AA"]  / (total_aa  if total_aa  else 1)
    df["vs_aa"]    = (df["ACT"] / df["AA"].replace(0, pd.NA)) - 1
    df["pct_p"]    = (df["ACT"] - df["PPTO"]) / df["PPTO"].replace(0, pd.NA)
    df["pct_ppto"] = df["PPTO"] / (total_ppto if total_ppto else 1)
    df["alc"]      = df["ACT"] / df["PPTO"].replace(0, pd.NA)
    return df

def _prepara_niveles(df_f):
    orden = [
        "Ventas","Costo","Margen","Marketing","Contribucion",
        "Gastos Operativos","Alquiler","Mantenimiento","Administracion Central",
        "Royaltie","Depreciacion","Resultado Operativo","Impuestos a la Renta",
        "Extraordinário Cash","Extraordinário No Cash","Diferencia Cambiaria",
        "Provisiones","Resultado Neto","Flujo","EBITDA","F-Flujo"
    ]
    for c in ["Cuentas","SubCuenta"]:
        if c not in df_f.columns:
            df_f[c] = ""
    df_f["Cuentas"]   = df_f["Cuentas"].fillna("").astype(str).str.strip()
    df_f["SubCuenta"] = df_f["SubCuenta"].fillna("").astype(str).str.strip()

    niv0_base = df_f.groupby("Cuentas", as_index=False)[["ACT","AA","PPTO"]].sum()
    niv1_base = (
        df_f[df_f["SubCuenta"].str.strip() != ""]
        .groupby(["Cuentas","SubCuenta"], as_index=False)[["ACT","AA","PPTO"]]
        .sum()
    )

    third = _third_level_col(df_f)
    if third:
        df_f[third] = df_f[third].fillna("").astype(str).str.strip()
        mask_lvl2 = (df_f["SubCuenta"].str.strip() != "") & (df_f[third].str.strip() != "")
        niv2_base = (
            df_f[mask_lvl2]
            .groupby(["Cuentas","SubCuenta",third], as_index=False)[["ACT","AA","PPTO"]]
            .sum()
            .rename(columns={third: "Linea"})
        )
    else:
        niv2_base = pd.DataFrame(columns=["Cuentas","SubCuenta","Linea","ACT","AA","PPTO"])

    total_act = niv0_base.loc[niv0_base["Cuentas"]=="Ventas","ACT"].sum() or niv0_base["ACT"].sum() or 1
    total_aa  = niv0_base.loc[niv0_base["Cuentas"]=="Ventas","AA"].sum()  or niv0_base["AA"].sum()  or 1
    total_ppt = niv0_base.loc[niv0_base["Cuentas"]=="Ventas","PPTO"].sum() or niv0_base["PPTO"].sum() or 1

    niv0 = _calc(niv0_base, total_act, total_aa, total_ppt)
    niv1 = _calc(niv1_base, total_act, total_aa, total_ppt)
    niv2 = _calc(niv2_base, total_act, total_aa, total_ppt) if not niv2_base.empty else pd.DataFrame(
        columns=["Cuentas","SubCuenta","Linea","ACT","AA","PPTO","pct_act","pct_aa","vs_aa","pct_p","pct_ppto","alc"]
    )

    niv0["__orden"] = niv0["Cuentas"].apply(lambda x: (orden.index(x) if x in orden else len(orden)+1, x))
    niv0.sort_values("__orden", inplace=True)
    niv0.reset_index(drop=True, inplace=True)
    return niv0, niv1, niv2

def _arma_vista(n0, n1, n2, expanded):
    filas = []
    ordenar_n2_para = {"gastos generales","gastos personal"}

    for _, p in n0.iterrows():
        key0 = ('n0', p["Cuentas"])
        filas.append({
            "Cuenta": p["Cuentas"], "Nodo":"n0",
            "CuentaKey": p["Cuentas"], "SubKey":"", "LineaKey":"",
            "nivel":0, "es_hijo":0, "key":str(key0),
            "ACT":p["ACT"], "pct_act":p["pct_act"], "AA":p["AA"], "pct_aa":p["pct_aa"],
            "vs_aa":p["vs_aa"], "pct_p":p["pct_p"], "PPTO":p["PPTO"], "pct_ppto":p["pct_ppto"], "alc":p["alc"]
        })
        if key0 in expanded:
            hijos = n1[n1["Cuentas"] == p["Cuentas"]]
            for _, h in hijos.iterrows():
                sub = str(h["SubCuenta"]).strip()
                key1 = ('n1', h["Cuentas"], sub)
                filas.append({
                    "Cuenta": "  • " + sub, "Nodo":"n1",
                    "CuentaKey": h["Cuentas"], "SubKey": sub, "LineaKey":"",
                    "nivel":1, "es_hijo":0, "key":str(key1),
                    "ACT":h["ACT"], "pct_act":h["pct_act"], "AA":h["AA"], "pct_aa":h["pct_aa"],
                    "vs_aa":h["vs_aa"], "pct_p":h["pct_p"], "PPTO":h["PPTO"], "pct_ppto":h["pct_ppto"], "alc":h["alc"]
                })
                if key1 in expanded:
                    can_open_n2 = ((h["Cuentas"], sub) in N2_ALLOWED_FOR_N1) and (h["Cuentas"] not in ONE_LEVEL_N0)
                    if can_open_n2:
                        nietos = n2[(n2["Cuentas"] == h["Cuentas"]) & (n2["SubCuenta"] == sub)]
                        if _norm(sub) in ordenar_n2_para and not nietos.empty:
                            nietos = nietos.sort_values(by="ACT", ascending=True)
                        for _, g in nietos.iterrows():
                            filas.append({
                                "Cuenta": "    · " + str(g["Linea"]), "Nodo":"n2",
                                "CuentaKey": g["Cuentas"], "SubKey": sub, "LineaKey": str(g["Linea"]),
                                "nivel":2, "es_hijo":1, "key": str(('n2', g["Cuentas"], sub, str(g["Linea"]))),
                                "ACT":g["ACT"], "pct_act":g["pct_act"], "AA":g["AA"], "pct_aa":g["pct_aa"],
                                "vs_aa":g["vs_aa"], "pct_p":g["pct_p"], "PPTO":g["PPTO"], "pct_ppto":g["pct_ppto"], "alc":g["alc"]
                            })
    cols = ["Cuenta","Nodo","CuentaKey","SubKey","LineaKey","nivel","es_hijo","key",
            "ACT","pct_act","AA","pct_aa","vs_aa","pct_p","PPTO","pct_ppto","alc"]
    return pd.DataFrame(filas, columns=cols)

def _grid_format(gb):
    gb.configure_default_column(headerClass="center-header")

    num_fmt = JsCode("""
    function(params){
      if(params.value===null||params.value===undefined||isNaN(params.value)) return '';
      return Number(params.value).toLocaleString();
    }""")

    entero_fmt = JsCode("""
    function(params){
      if(params.value===null||params.value===undefined||isNaN(params.value)) return '';
      return Math.floor(Number(params.value)).toLocaleString('es-ES');
    }""")

    pct1_fmt = JsCode("""
    function(params){
      if(params.value===null||params.value===undefined||isNaN(params.value)) return '';
      return (Number(params.value)*100).toFixed(1)+' %';
    }""")

    gb.configure_column("Cuenta", cellStyle=cuenta_cellstyle)
    for col in ["ACT","AA","PPTO","pct_act","pct_aa","vs_aa","pct_p","pct_ppto","alc"]:
        gb.configure_column(col, cellStyle=totalizer_cellstyle)

    for c in ["ACT","AA","PPTO"]:
        gb.configure_column(c, valueFormatter=entero_fmt, type=["numericColumn"], min_width=90,
                            filter=False, floatingFilter=False, suppressMenu=True)

    gb.configure_column("pct_act",  header_name="%",     valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)
    gb.configure_column("pct_aa",   header_name="%",     valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)
    gb.configure_column("vs_aa",    header_name="VS AA", valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)
    gb.configure_column("pct_p",    header_name="%P",    valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)
    gb.configure_column("pct_ppto", header_name="%",     valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)
    gb.configure_column("alc",      header_name="ALC",   valueFormatter=pct1_fmt,
                        min_width=60, maxWidth=90, filter=False, floatingFilter=False, suppressMenu=True)

    gb.configure_grid_options(headerHeight=35, suppressMovableColumns=True)
    gb.configure_column("Cuenta", header_name="Cuenta", headerClass="center-header")
    return gb

def _get_selected_row(grid_response):
    sel = grid_response.get("selected_rows", [])
    if isinstance(sel, list):
        return sel[0] if len(sel) > 0 else None
    if isinstance(sel, pd.DataFrame):
        return sel.iloc[0].to_dict() if not sel.empty else None
    return None

def show():
    st.title("📊 Estado de Resultados")

    if "expanded_keys" not in st.session_state:
        st.session_state.expanded_keys = set()
    if "grid_nonce" not in st.session_state:
        st.session_state.grid_nonce = 0

    mtime = os.path.getmtime(ARCHIVO)
    df = cargar_datos(ARCHIVO, mtime)

    anio, periodo, mes, sucursal = _layout_filtros(df)
    df_f = _aplicar_filtros(df, anio, periodo, mes, sucursal)

    n0, n1, n2 = _prepara_niveles(df_f)
    vista = _arma_vista(n0, n1, n2, st.session_state.expanded_keys)

    gb = GridOptionsBuilder.from_dataframe(vista)

    gb.configure_default_column(groupable=False, editable=False, resizable=True, sortable=True,
                                suppressMenu=True, filter=False, floatingFilter=False, wrapText=False,
                                autoHeaderHeight=True, headerClass="center-header")

    gb.configure_column("Cuenta", header_name="Cuenta", headerClass="center-header",
                        cellStyle=cuenta_cellstyle, min_width=240, tooltipField="Cuenta", pinned="left")

    gb_num_cols = ["ACT","AA","PPTO","pct_act","pct_aa","vs_aa","pct_p","pct_ppto","alc"]
    for col in gb_num_cols:
        gb.configure_column(col, cellStyle=totalizer_cellstyle,
                            type=["numericColumn","rightAligned"], min_width=110)

    empty_getter = JsCode("function(params){ return ''; }")
    for tech_col in ["Nodo","CuentaKey","SubKey","LineaKey"]:
        gb.configure_column(tech_col, header_name=tech_col, valueGetter=empty_getter,
                            width=1, maxWidth=1, minWidth=1)
    gb.configure_column("nivel", hide=True)
    gb.configure_column("es_hijo", hide=True)
    gb.configure_column("key", hide=True)

    gb = _grid_format(gb)

    gb.configure_grid_options(rowHeight=24, headerHeight=26, domLayout='normal',
                              enableFilter=False, floatingFilter=False)

    grid_options = gb.build()

    custom_css = {
        ".ag-cell": {"padding": "1px 4px", "line-height": "1.15"},
        ".ag-header": {"min-height": "26px"},
        ".ag-header-cell": {"padding": "1px 4px"},
        ".ag-row": {"font-size": "14px"},
        ".ag-header-cell-label": {
            "display":"flex","align-items":"center","justify-content":"center",
            "width":"100%","position":"relative",
        },
        ".ag-header-cell-label [ref='eText']": {
            "margin":"0 auto","text-align":"center","width":"100%","display":"block",
        },
        ".ag-header-cell-label > span.ag-header-icon": {"position":"absolute","right":"6px"},
    }

    auto_size_js = JsCode("""
    function(params){
        var ids = [];
        params.columnApi.getAllColumns().forEach(function(c){
            ids.push(c.getColId());
        });
        params.columnApi.autoSizeColumns(ids, false);
    }
    """)

    gb.configure_selection(selection_mode="single", use_checkbox=False)

    left, mid, right = st.columns([1, 9, 1])
    with mid:
        grid = AgGrid(
            vista,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            fit_columns_on_grid_load=True,
            height=600,
            allow_unsafe_jscode=True,
            theme="balham",
            key=f"grid_tree_{len(st.session_state.expanded_keys)}_{st.session_state.grid_nonce}_{st.session_state.get('_filters_nonce', 0)}",
            custom_css=custom_css,
            custom_js_events={
                "onGridReady": auto_size_js,
                "onFirstDataRendered": auto_size_js,
                "onColumnResized": auto_size_js,
                "onGridSizeChanged": auto_size_js
            }
        )

    row = _get_selected_row(grid)
    if row:
        nodo = (row.get("Nodo") or "").strip()

        if nodo == "n0":
            cuenta = (row.get("CuentaKey") or "").strip()
            if cuenta in NO_EXPAND_N0:
                return
        elif nodo == "n1":
            cuenta = (row.get("CuentaKey") or "").strip()
            sub = (row.get("SubKey") or "").strip() or _sub_from_display(row.get("Cuenta"))
            if ((cuenta, sub) not in N2_ALLOWED_FOR_N1) or (cuenta in ONE_LEVEL_N0):
                return

        if nodo == "n0":
            key0 = ('n0', row.get("CuentaKey"))
            if key0 in st.session_state.expanded_keys:
                st.session_state.expanded_keys.remove(key0)
            else:
                st.session_state.expanded_keys.add(key0)

        elif nodo == "n1":
            sub = (row.get("SubKey") or "").strip() or _sub_from_display(row.get("Cuenta"))
            key1 = ('n1', row.get("CuentaKey"), sub)
            if key1 in st.session_state.expanded_keys:
                st.session_state.expanded_keys.remove(key1)
            else:
                st.session_state.expanded_keys.add(key1)

        st.session_state.grid_nonce += 1
        rerun_app()