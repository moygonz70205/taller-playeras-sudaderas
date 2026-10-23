import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Taller - Playeras y Sudaderas", page_icon="👕", layout="wide")

# --- CONEXIÓN A SUPABASE ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error de configuración con Supabase. Asegúrate de crear el archivo secrets.toml. Detalle: {e}")
    st.stop()

# --- MENÚ LATERAL ---
st.sidebar.title("🧵 Taller Control")
menu = st.sidebar.radio(
    "Menú Principal",
    [
        "🏠 Inicio",
        "📦 Inventario y Stock",
        "🛍️ Módulo de Ventas",
        "💵 Tesorería y Finanzas",
        "📜 Historial de Movimientos",
        "📈 Reporte del Negocio",
        "⚙️ Configuración de Productos"
    ]
)

# ==========================================
# 0. INICIO / DASHBOARD
# ==========================================
if menu == "🏠 Inicio":
    st.title("🏠 Panel de Control Operativo")
    st.markdown("Bienvenido al sistema de gestión de tu taller.")
    
    col1, col2, col3 = st.columns(3)
    try:
        prods = supabase.table("productos_config").select("*", count="exact").execute()
        cuentas = supabase.table("finanzas_cuentas").select("*").execute()
        
        with col1:
            st.metric("Productos Registrados", len(prods.data) if prods.data else 0)
        with col2:
            total_dinero = sum(c['saldo'] for c in cuentas.data) if cuentas.data else 0.0
            st.metric("Capital Total en Cuentas", f"${total_dinero:,.2f}")
        with col3:
            st.metric("Estado del Sistema", "🟢 En Línea / Supabase OK")
    except Exception as e:
        st.warning("Conectado, cargando métricas iniciales...")

    st.markdown("---")
    st.info("💡 Usa el menú de la izquierda para navegar entre tus módulos.")

# ==========================================
# 1. CONFIGURACIÓN DE PRODUCTOS
# ==========================================
elif menu == "⚙️ Configuración de Productos":
    st.title("⚙️ Configuración de Márgenes por Clave de Producto")
    st.markdown("Selecciona el tipo de producto base (Ej. Playera Básica | DTF Mediano). Los cambios se aplicarán automáticamente a todas las variantes que compartan esta clave.")

    try:
        prods_res = supabase.table("productos_config").select("*").execute()
        if prods_res.data:
            claves_dict = {}
            for p in prods_res.data:
                clave_key = f"{p['modelo']} ➔ {p['tela']} ➔ DTF: {p['tamanio_dtf']}"
                if clave_key not in claves_dict:
                    claves_dict[clave_key] = p

            sel_clave = st.selectbox("🔍 Buscar Clave de Producto a Configurar", list(claves_dict.keys()))
            p_ejemplo = claves_dict[sel_clave]
            
            st.markdown("---")
            st.info(f"Configurando porcentajes para: **{sel_clave}**")
            
            with st.form("form_editar_config_masiva"):
                col_u1, col_u2, col_u3 = st.columns(3)
                with col_u1:
                    n_reinversion = st.number_input("% Utilidad para Reinversión", value=float(p_ejemplo['pct_reinversion']))
                with col_u2:
                    n_propietario = st.number_input("% Utilidad para Propietario", value=float(p_ejemplo['pct_propietario']))
                with col_u3:
                    n_emergencias = st.number_input("% Utilidad para Emergencias", value=float(p_ejemplo['pct_emergencias']))
                
                total_pct = n_reinversion + n_propietario + n_emergencias
                if total_pct != 100.0:
                    st.warning(f"⚠️ La suma de utilidades es {total_pct}%. Lo ideal es que sumen 100%.")

                btn_actualizar_masivo = st.form_submit_button("💾 Actualizar Porcentajes para este Grupo")
                
                if btn_actualizar_masivo:
                    supabase.table("productos_config").update({
                        "pct_reinversion": n_reinversion,
                        "pct_propietario": n_propietario,
                        "pct_emergencias": n_emergencias
                    }).eq("modelo", p_ejemplo['modelo']).eq("tela", p_ejemplo['tela']).eq("tamanio_dtf", p_ejemplo['tamanio_dtf']).execute()
                    
                    st.success("¡Porcentajes actualizados con éxito!")
                    st.balloons()
        else:
            st.warning("⚠️ Aún no hay productos registrados. Ve primero a 'Inventario y Stock' para crear uno.")
    except Exception as e:
        st.error(f"Error al cargar la configuración: {e}")

# ==========================================
# 2. INVENTARIO Y STOCK
# ==========================================
elif menu == "📦 Inventario y Stock":
    st.title("📦 Inventario y Control de Almacén")
    
    tab1, tab2, tab3 = st.tabs([
        "📋 Ver Inventario Registrado", 
        "➕ Registrar Entrada de Stock", 
        "✨ Dar de Alta Producto Nuevo"
    ])
    
    with tab1:
        st.subheader("Catálogo de Prendas Actuales")
        try:
            response = supabase.table("productos_config").select("*").execute()
            if response.data:
                st.dataframe(response.data, use_container_width=True)
            else:
                st.info("Aún no hay productos registrados.")
        except Exception as e:
            st.error(f"Error al cargar inventario: {e}")

    with tab2:
        st.subheader("Añadir Stock a un Producto Existente")
        try:
            prods = supabase.table("productos_config").select("id, modelo, tela, color, talla, tamanio_dtf").execute()
            if prods.data:
                opciones = {f"{p['modelo']} | {p['tela']} | {p['color']} | Talla: {p['talla']} | DTF: {p['tamanio_dtf']}": p['id'] for p in prods.data}
                sel_prod = st.selectbox("Selecciona la prenda a reponer", list(opciones.keys()))
                cant_entrada = st.number_input("Cantidad de piezas a agregar", min_value=1, value=10)
                
                if st.button("📥 Registrar Entrada"):
                    prod_id = opciones[sel_prod]
                    supabase.table("historial_movimientos").insert({
                        "tipo": "ENTRADA",
                        "detalle": f"Ingreso de stock para producto ID {prod_id}",
                        "cantidad": cant_entrada,
                        "monto": 0.0
                    }).execute()
                    st.success(f"¡Se registraron {cant_entrada} piezas con éxito!")
                    st.balloons()
            else:
                st.info("Primero da de alta productos en la tercera pestaña.")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab3:
        st.subheader("✨ Dar de Alta Producto o Variante")
        st.markdown("Crea tu prenda definiendo sus características físicas, costos y precio de venta.")
        
        with st.form("form_crear_producto_puro"):
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                familia_libre = st.text_input("Familia Principal", placeholder="Ej. Playera, Sudadera...")
                sub_libre = st.text_input("Tipo / Calidad", placeholder="Ej. Básica, Premium...")
                color_libre = st.text_input("Color", placeholder="Ej. Negro, Blanco, Gris...")
            with col_l2:
                talla_libre = st.text_input("Talla", placeholder="Ej. CH, M, G, 2XL...")
                dtf_libre = st.text_input("Tamaño de DTF", placeholder="Ej. DTF Mediano, DTF Grande, Sin DTF...")
            
            st.markdown("---")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                costo_produccion = st.number_input("Costo de Fabricación Unitario ($)", min_value=0.0, value=100.0)
            with col_p2:
                precio_venta = st.number_input("Precio de Venta al Público ($)", min_value=0.0, value=250.0)

            btn_guardar_puro = st.form_submit_button("🚀 Guardar Producto en el Inventario")
            
            if btn_guardar_puro:
                if not familia_libre or not color_libre:
                    st.warning("Por favor completa al menos la familia y el color.")
                else:
                    try:
                        data_puro = {
                            "modelo": familia_libre,
                            "tela": sub_libre,
                            "color": color_libre,
                            "tamanio_dtf": dtf_libre,
                            "talla": talla_libre,
                            "costo_produccion": costo_produccion,
                            "precio_venta": precio_venta,
                            "pct_reinversion": 50.0,
                            "pct_propietario": 30.0,
                            "pct_emergencias": 20.0
                        }
                        supabase.table("productos_config").insert(data_puro).execute()
                        st.success(f"¡Guardado con éxito: {familia_libre} {sub_libre} ({color_libre}, {talla_libre})!")
                        st.balloons()
                    except Exception as ex:
                        st.error(f"Error al guardar el producto: {ex}")

# ==========================================
# 3. MÓDULO DE VENTAS
# ==========================================
elif menu == "🛍️ Módulo de Ventas":
    st.title("🛍️ Punto de Venta y Salidas")
    st.markdown("Registra las ventas. El sistema aplicará los porcentajes configurados para este tipo de producto.")

    try:
        prods = supabase.table("productos_config").select("*").execute()
        if prods.data:
            opciones_v = {f"{p['modelo']} {p['tela']} - {p['color']} | Talla: {p['talla']} | DTF: {p['tamanio_dtf']} (${p['precio_venta']})": p for p in prods.data}
            sel_v = st.selectbox("Selecciona la prenda vendida", list(opciones_v.keys()))
            prod_elegido = opciones_v[sel_v]
            
            cant_venta = st.number_input("Cantidad de piezas vendidas", min_value=1, value=1)
            precio_unit = prod_elegido['precio_venta']
            costo_unit = prod_elegido['costo_produccion']
            
            total_venta = precio_unit * cant_venta
            utilidad_total = (precio_unit - costo_unit) * cant_venta
            
            st.markdown(f"### Total Venta: **${total_venta:,.2f}**")
            st.markdown(f"### Utilidad Neta Total: **${utilidad_total:,.2f}**")
            
            if st.button("💰 Confirmar Venta y Distribuir Capital"):
                supabase.table("historial_movimientos").insert({
                    "tipo": "VENTA",
                    "detalle": f"Venta de {cant_venta} pieza(s) de {prod_elegido['modelo']} {prod_elegido['tela']} ({prod_elegido['color']})",
                    "cantidad": cant_venta,
                    "monto": total_venta
                }).execute()
                
                cuentas_res = supabase.table("finanzas_cuentas").select("*").execute()
                if cuentas_res.data:
                    for c in cuentas_res.data:
                        nombre = c['nombre_cuenta']
                        saldo_actual = c['saldo']
                        incremento = 0.0
                        
                        if "Dinero Negocio" in nombre:
                            incremento = (costo_unit * cant_venta)
                        elif utilidad_total > 0:
                            if "Reinversión" in nombre:
                                incremento = utilidad_total * (prod_elegido['pct_reinversion'] / 100.0)
                            elif "Propietario" in nombre:
                                incremento = utilidad_total * (prod_elegido['pct_propietario'] / 100.0)
                            elif "Emergencias" in nombre:
                                incremento = utilidad_total * (prod_elegido['pct_emergencias'] / 100.0)
                        
                        nuevo_saldo = saldo_actual + incremento
                        supabase.table("finanzas_cuentas").update({"saldo": nuevo_saldo}).eq("id", c['id']).execute()

                st.success("¡Venta registrada y fondos distribuidos correctamente!")
                st.balloons()
        else:
            st.info("No hay productos disponibles. Da de alta algunos en 'Inventario y Stock'.")
    except Exception as e:
        st.error(f"Error en módulo de ventas: {e}")

# ==========================================
# 4. TESORERÍA Y FINANZAS (CON NOMBRE DEFINITIVO UNIFICADO)
# ==========================================
elif menu == "💵 Tesorería y Finanzas":
    st.title("💵 Tesorería y Cubetas de Capital")
    st.markdown("Consulta tus saldos, el desglose visual de tu capital operativo y realiza gastos o transferencias.")

    try:
        cuentas_res = supabase.table("finanzas_cuentas").select("*").execute()
        if cuentas_res.data:
            saldo_negocio = sum(c['saldo'] for c in cuentas_res.data if "Dinero Negocio" in c['nombre_cuenta'])
            saldo_reinversion = sum(c['saldo'] for c in cuentas_res.data if "Reinversión" in c['nombre_cuenta'])
            capital_operacion_total = saldo_negocio + saldo_reinversion
            
            # --- MÉTRICAS DE ENCABEZADO ---
            c_prop = next((c['saldo'] for c in cuentas_res.data if "Propietario" in c['nombre_cuenta']), 0.0)
            c_emerg = next((c['saldo'] for c in cuentas_res.data if "Emergencias" in c['nombre_cuenta']), 0.0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="💼 Capital de Operación y Crecimiento", value=f"${capital_operacion_total:,.2f}")
            with col2:
                st.metric(label="👤 Rendimiento Propietario", value=f"${c_prop:,.2f}")
            with col3:
                st.metric(label="🛡️ Fondo de Emergencias", value=f"${c_emerg:,.2f}")
            
            st.markdown("---")
            
            # --- DESGLOSE VISUAL ---
            st.subheader("📊 Composición del Capital de Operación y Crecimiento")
            if capital_operacion_total > 0:
                pct_neg = (saldo_negocio / capital_operacion_total) * 100
                pct_reinv = (saldo_reinversion / capital_operacion_total) * 100
            else:
                pct_neg = pct_reinv = 50.0

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"📦 **Recuperación de Costos:** ${saldo_negocio:,.2f} *({pct_neg:.1f}%)*")
            with col_d2:
                st.markdown(f"📈 **Utilidad para Reinversión:** ${saldo_reinversion:,.2f} *({pct_reinv:.1f}%)*")
            
            st.progress(pct_neg / 100.0, text=f"Distribución interna (Costos: {pct_neg:.1f}% | Reinversión: {pct_reinv:.1f}%)")
            
            st.markdown("---")
            
            # Lista limpia de opciones (sin duplicados ni cuentas sueltas)
            opciones_cuentas_limpias = [
                "💼 Capital de Operación y Crecimiento",
                "👤 Rendimiento Propietario",
                "🛡️ Fondo de Emergencias"
            ]
            
            # --- PESTAÑAS DE GASTOS Y TRANSFERENCIAS ---
            tab_gasto, tab_transf = st.tabs(["💸 Registrar Gasto Operativo", "🔄 Transferir entre Cuentas"])
            
            with tab_gasto:
                with st.form("form_gasto_unificado"):
                    detalle_gasto = st.text_input("Descripción del gasto (ej. Compra rollos DTF, luz...)")
                    monto_gasto = st.number_input("Monto del gasto ($)", min_value=0.0, value=500.0)
                    cta_gasto = st.selectbox("Origen del Dinero", opciones_cuentas_limpias)
                    
                    if st.form_submit_button("Registrar Gasto"):
                        supabase.table("historial_movimientos").insert({
                            "tipo": "GASTO",
                            "detalle": f"Gasto de [{cta_gasto}]: {detalle_gasto}",
                            "cantidad": 1,
                            "monto": monto_gasto
                        }).execute()
                        
                        if "Capital de Operación y Crecimiento" in cta_gasto:
                            monto_restante = monto_gasto
                            for c in cuentas_res.data:
                                if "Dinero Negocio" in c['nombre_cuenta'] and monto_restante > 0:
                                    available = c['saldo']
                                    a_descontar = min(available, monto_restante)
                                    supabase.table("finanzas_cuentas").update({"saldo": available - a_descontar}).eq("id", c['id']).execute()
                                    monto_restante -= a_descontar
                                elif "Reinversión" in c['nombre_cuenta'] and monto_restante > 0:
                                    available = c['saldo']
                                    a_descontar = min(available, monto_restante)
                                    supabase.table("finanzas_cuentas").update({"saldo": available - a_descontar}).eq("id", c['id']).execute()
                                    monto_restante -= a_descontar
                        else:
                            for c in cuentas_res.data:
                                if ("Propietario" in c['nombre_cuenta'] and "Propietario" in cta_gasto) or \
                                   ("Emergencias" in c['nombre_cuenta'] and "Emergencias" in cta_gasto):
                                    nuevo_saldo = c['saldo'] - monto_gasto
                                    supabase.table("finanzas_cuentas").update({"saldo": nuevo_saldo}).eq("id", c['id']).execute()
                        
                        st.success("¡Gasto registrado correctamente!")
                        st.balloons()

            with tab_transf:
                with st.form("form_transferencia_limpia"):
                    st.markdown("Mueve saldo fácilmente entre tus fondos principales.")
                    
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        cta_origen = st.selectbox("Cuenta Origen", opciones_cuentas_limpias, key="t_orig")
                    with col_t2:
                        cta_destino = st.selectbox("Cuenta Destino", opciones_cuentas_limpias, key="t_dest")
                        
                    monto_transf = st.number_input("Monto a transferir ($)", min_value=0.0, value=100.0)
                    
                    if st.form_submit_button("🔄 Realizar Transferencia"):
                        if cta_origen == cta_destino:
                            st.warning("El origen y el destino deben ser diferentes.")
                        else:
                            # Obtener saldo de origen
                            saldo_disponible = 0.0
                            if "Capital de Operación y Crecimiento" in cta_origen:
                                saldo_disponible = capital_operacion_total
                            elif "Propietario" in cta_origen:
                                saldo_disponible = c_prop
                            elif "Emergencias" in cta_origen:
                                saldo_disponible = c_emerg
                                
                            if saldo_disponible < monto_transf:
                                st.error("No hay suficiente dinero en la cuenta de origen seleccionada.")
                            else:
                                # 1. Descontar del origen
                                if "Capital de Operación y Crecimiento" in cta_origen:
                                    monto_rest = monto_transf
                                    for c in cuentas_res.data:
                                        if "Dinero Negocio" in c['nombre_cuenta'] and monto_rest > 0:
                                            avail = c['saldo']
                                            sub = min(avail, monto_rest)
                                            supabase.table("finanzas_cuentas").update({"saldo": avail - sub}).eq("id", c['id']).execute()
                                            monto_rest -= sub
                                        elif "Reinversión" in c['nombre_cuenta'] and monto_rest > 0:
                                            avail = c['saldo']
                                            sub = min(avail, monto_rest)
                                            supabase.table("finanzas_cuentas").update({"saldo": avail - sub}).eq("id", c['id']).execute()
                                            monto_rest -= sub
                                else:
                                    tag = "Propietario" if "Propietario" in cta_origen else "Emergencias"
                                    match_o = next((c for c in cuentas_res.data if tag in c['nombre_cuenta']), None)
                                    if match_o:
                                        supabase.table("finanzas_cuentas").update({"saldo": match_o['saldo'] - monto_transf}).eq("id", match_o['id']).execute()

                                # 2. Abonar al destino
                                if "Capital de Operación y Crecimiento" in cta_destino:
                                    match_r = next((c for c in cuentas_res.data if "Reinversión" in c['nombre_cuenta']), None)
                                    if match_r:
                                        supabase.table("finanzas_cuentas").update({"saldo": match_r['saldo'] + monto_transf}).eq("id", match_r['id']).execute()
                                else:
                                    tag_d = "Propietario" if "Propietario" in cta_destino else "Emergencias"
                                    match_d = next((c for c in cuentas_res.data if tag_d in c['nombre_cuenta']), None)
                                    if match_d:
                                        supabase.table("finanzas_cuentas").update({"saldo": match_d['saldo'] + monto_transf}).eq("id", match_d['id']).execute()
                                
                                supabase.table("historial_movimientos").insert({
                                    "tipo": "TRANSFERENCIA",
                                    "detalle": f"Transferencia de ${monto_transf:,.2f} desde [{cta_origen}] hacia [{cta_destino}]",
                                    "cantidad": 1,
                                    "monto": monto_transf
                                }).execute()
                                
                                st.success("¡Transferencia completada con éxito!")
                                st.balloons()
    except Exception as e:
        st.error(f"Error al cargar finanzas: {e}")

# ==========================================
# 5. HISTORIAL DE MOVIMIENTOS
# ==========================================
elif menu == "📜 Historial de Movimientos":
    st.title("📜 Bitácora General de Movimientos")
    try:
        hist = supabase.table("historial_movimientos").select("*").order("created_at", desc=True).execute()
        if hist.data:
            st.dataframe(hist.data, use_container_width=True)
        else:
            st.info("Aún no hay movimientos registrados.")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# ==========================================
# 6. REPORTE DEL NEGOCIO
# ==========================================
elif menu == "📈 Reporte del Negocio":
    st.title("📈 Analítica y Tendencia Comercial")
    try:
        ventas_res = supabase.table("historial_movimientos").select("*").eq("tipo", "VENTA").execute()
        gastos_res = supabase.table("historial_movimientos").select("*").eq("tipo", "GASTO").execute()
        
        total_ventas = sum(v['monto'] for v in ventas_res.data) if ventas_res.data else 0.0
        total_gastos = sum(g['monto'] for g in gastos_res.data) if gastos_res.data else 0.0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ingresos Totales", f"${total_ventas:,.2f}")
        with col2:
            st.metric("Gastos Totales", f"${total_gastos:,.2f}")
        with col3:
            st.metric("Balance Operativo", f"${total_ventas - total_gastos:,.2f}")
    except Exception as e:
        st.error(f"Error al generar reportes: {e}")