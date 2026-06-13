"""Spanish admin catalog.

Mirrors every key in en.py with identical placeholders. Interpolated values
(DB statuses, usernames, Stripe data, command names, env var names) are NOT
translated — only the surrounding labels are.
"""

ADMIN_MESSAGES = {
    # --- Sections / main menu ---------------------------------------------- #
    "menu.user_management": "Gestión de Usuarios",
    "menu.questions": "Preguntas",
    "menu.subscriptions": "Suscripciones y Pagos",
    "menu.system": "Configuración del Sistema",

    # --- Start / home ------------------------------------------------------- #
    "start.title": "👑 <b>AskBot — Administrador</b>",
    "start.body": (
        "Eres el administrador — <b>no se necesita verificación ni aprobación</b>.\n\n"
        "Usa el <b>teclado de abajo</b> (dos botones por fila) para abrir una sección, "
        "o usa los accesos directos <b>en línea</b> del siguiente mensaje.\n"
        "Todas las acciones de cada sección se manejan con botones."
    ),
    "home.title": "🏠 Panel Principal del Administrador",
    "home.desc": "Gestiona usuarios, preguntas, suscripciones y configuración del sistema desde un solo lugar.",
    "home.prompt": "Elige una sección abajo.",

    # --- Common ------------------------------------------------------------- #
    "nav.back": "◀ Atrás",
    "nav.home": "🏠 Inicio",
    "common.choose_option": "Elige una opción abajo.",
    "pg.prev": "⬅️ Anterior",
    "pg.next": "➡️ Siguiente",
    "pg.prev_arrow": "⬅️",
    "pg.next_arrow": "➡️",
    "btn.open_user": "👤 {tid}",

    # --- User Management dashboard ----------------------------------------- #
    "um.title": "👥 Gestión de Usuarios",
    "um.total": "📊 <b>{total}</b> usuarios en total",
    "um.line_active_expired": "🟢 Activos: <b>{active}</b>\xa0\xa0\xa0🔴 Expirados: <b>{expired}</b>",
    "um.line_grace_pending": "⏳ Gracia: <b>{grace}</b>\xa0\xa0\xa0📝 Pendientes: <b>{pending}</b>",
    "um.hint": "Toca una tarjeta para ver detalles, o busca un usuario específico.",
    "um.card_active": "🟢 Activos · {n}",
    "um.card_expired": "🔴 Expirados · {n}",
    "um.card_grace": "⏳ Gracia · {n}",
    "um.card_pending": "📝 Pendientes · {n}",
    "um.card_all": "👥 Todos los Usuarios · {n}",
    "um.card_search": "🔍  Buscar Usuario  🔍",

    # Filtered list titles
    "filter.active_title": "🟢 Miembros Activos",
    "filter.expired_title": "🔴 Miembros Expirados",
    "filter.grace_title": "⏳ Usuarios en Periodo de Gracia",

    # All-users list
    "ul.empty_title": "👥 Resumen de Gestión de Usuarios",
    "ul.empty_body": "Todavía no hay usuarios registrados en el sistema.",
    "ul.empty_hint": "Los usuarios aparecerán aquí en cuanto comiencen el registro.",
    "ul.header": "<b>Todos los usuarios</b> ({total}) — página {page}",
    "ul.summary_line": (
        "• <code>{tid}</code> {name} {un}\n"
        "  estado: <b>{status}</b> | sub: <b>{sub}</b> {plan}\n"
        "  preguntas usadas: <b>{used}</b> / {limit}"
    ),

    # Filtered list
    "uf.empty_body": "Ningún miembro coincide con este estado en este momento.",
    "uf.empty_hint": "Aparecerán aquí automáticamente a medida que cambien los estados de suscripción.",
    "uf.header": "<b>{title}</b> ({total}) — página {page}",

    # Pending approval
    "up.empty_title": "📋 Cola de Aprobación Pendiente",
    "up.empty_body": "Actualmente no hay usuarios esperando aprobación.",
    "up.empty_hint": "Las nuevas solicitudes de acceso aparecerán aquí en cuanto lleguen.",
    "up.header": "<b>Aprobación pendiente</b> ({n})\n\nAbre un usuario:",

    # --- User detail -------------------------------------------------------- #
    "ud.not_found_popup": "Usuario {tid} no encontrado.\n\nPuede que haya sido eliminado o que nunca se registrara.",
    "ud.block": (
        "<b>Usuario</b> <code>{tid}</code>\n"
        "Nombre: {name}\n"
        "Usuario: {username}\n"
        "Aprobación: <b>{approval}</b>\n"
        "Categoría de Usuario: <b>{category}</b>\n"
        "Preguntas usadas: <b>{used}</b> / límite {limit}\n\n"
        "{sub_block}"
    ),
    "btn.approve": "✅ Aprobar",
    "btn.reject": "❌ Rechazar",
    "btn.reset_user": "🔄 Restablecer usuario",
    "btn.expire_sub": "⏹ Expirar suscripción",
    "btn.grace": "⏳ Gracia",
    "btn.activate_sub": "▶️ Activar sub",
    "btn.remove_vip": "🚫 Quitar de VIP",

    # Approve
    "approve.cannot": "No se puede aprobar a este usuario desde su estado actual.",

    # Reject
    "rj.title": "❌ Rechazar Solicitud de Acceso",
    "rj.desc": (
        "Elige un motivo para rechazar a este usuario. Será notificado y "
        "eliminado del grupo VIP si actualmente es miembro."
    ),
    "rj.prompt": "Elige un motivo abajo.",
    "rj.reason_standards": "Estándares",
    "rj.reason_spam": "Spam",
    "rj.reason_other": "Otro",
    "rj.failed": "Error al rechazar",

    # Reset
    "reset.confirm_btn": "⚠️ Confirmar restablecimiento",
    "reset.ask": "<b>Restablecer usuario</b>\n\nEsto elimina el registro del usuario, la suscripción, los pagos y las preguntas.",
    "reset.done": "Restablecimiento completado",
    "reset.failed": "Error al restablecer",
    "reset.removed": "Usuario <code>{tid}</code> eliminado de la base de datos.",
    "reset.failed_page": "Error al restablecer.",

    # VIP remove
    "vip.not_configured": "Grupo VIP no configurado",
    "vip.telegram_err": "Telegram: {err}",

    # --- ID search ---------------------------------------------------------- #
    "ids.btn_cancel": "❌ Cancelar",
    "ids.prompt": (
        "<b>🔍 Buscar Usuario por ID de Telegram</b>\n\n"
        "{sep}\n\n"
        "Por favor envía el ID de Telegram del usuario.\n\n"
        "<i>Puedes escribirlo manualmente o pegarlo desde el portapapeles. "
        "Los ID de Telegram son numéricos y normalmente tienen entre 5 y 15 dígitos.</i>\n\n"
        "{sep}"
    ),
    "ids.invalid": (
        "<b>❌ ID de Telegram Inválido</b>\n\n"
        "{sep}\n\n"
        "El valor que enviaste no parece un ID de usuario de Telegram.\n\n"
        "Por favor envía un ID de Telegram numérico válido — normalmente entre 5 y 15 dígitos.\n\n"
        "{sep}"
    ),
    "ids.cancelled": "Cancelado",
    "ids.lookup_empty_title": "🔍 Resultado de Búsqueda de Usuario",
    "ids.lookup_empty_body": "No hay ningún usuario registrado con el ID de Telegram <code>{tid}</code>.",
    "ids.lookup_empty_hint": "Verifica el ID e inténtalo de nuevo, o regresa a Gestión de Usuarios.",

    # --- Questions ---------------------------------------------------------- #
    "qm.title": "📌 Sección de Gestión de Preguntas",
    "qm.desc": (
        "Ver preguntas pendientes que esperan respuesta o explorar el historial "
        "completo de preguntas enviadas por los usuarios."
    ),
    "qm.btn_pending": "📌 Pendientes ({n})",
    "qm.btn_all": "📚 Todas las Preguntas Enviadas ({n})",
    "qm.btn_export_pending": "📤 Exportar Pendientes",
    "qm.btn_export_all": "📤 Exportar Todo",
    # Question export dataset names (caption + sheet title) + column headers.
    "qexport.name_pending": "Preguntas Pendientes",
    "qexport.name_all": "Todas las Preguntas",
    "qexport.col_id": "ID de Pregunta",
    "qexport.col_user_id": "ID de Usuario de Telegram",
    "qexport.col_username": "Nombre de Usuario",
    "qexport.col_full_name": "Nombre Completo",
    "qexport.col_status": "Estado",
    "qexport.col_type": "Tipo de Pregunta",
    "qexport.col_text": "Pregunta",
    "qexport.col_reply": "Respuesta del Administrador",
    "qexport.col_created": "Fecha de Creación",
    "qexport.col_answered": "Fecha de Respuesta",

    "q.pending_empty_title": "📌 Cola de Preguntas Pendientes",
    "q.pending_empty_body": "No hay preguntas pendientes en este momento.",
    "q.pending_empty_hint": "Las preguntas que esperan respuesta aparecerán aquí en cuanto los usuarios las envíen.",
    "q.pending_header": "<b>Preguntas pendientes</b> ({n})",
    "q.hist_empty_title": "📚 Resumen del Historial de Preguntas",
    "q.hist_empty_body": "Aún no se ha registrado ninguna pregunta.",
    "q.hist_empty_hint": "Cada pregunta de usuario (Rápida o Legal VIP) se registrará aquí.",
    "q.hist_header": "<b>Todas las preguntas</b> ({n})",
    "q.detail": (
        "<b>Pregunta #{id}</b>\n"
        "Usuario: <code>{uid}</code> (@{un})\n"
        "Estado: <b>{status}</b>\n"
        "Creada: {created}\n\n"
        "<b>Texto</b>\n{text}\n"
    ),
    "q.admin_reply_block": "\n<b>Respuesta del administrador</b>\n{reply}\n",
    "q.btn_compose": "✍️ Redactar respuesta",
    "q.not_found": "No encontrado",
    "q.compose_title": "✍️ Modo de Redacción de Respuesta",
    "q.compose_desc": (
        "Envía tu <b>siguiente mensaje de texto</b> en este chat (no un comando). "
        "Se entregará al usuario y la pregunta se marcará como respondida.\n\n"
        "<i>Este es el único paso que usa un mensaje normal — después de que "
        "pulsaste el botón.</i>"
    ),
    "q.compose_prompt": "Escribe tu respuesta ahora, o pulsa Cancelar.",
    "q.btn_cancel_compose": "❌ Cancelar redacción",
    "q.compose_cancelled_title": "📝 Redacción de Respuesta Cancelada",
    "q.compose_cancelled_body": "La respuesta pendiente se descartó — no se envió nada.",
    "q.compose_cancelled_hint": "Usa el menú de Preguntas abajo para elegir otra pregunta.",
    "q.no_longer_pending": "La pregunta ya no está pendiente.",
    "q.user_blocked": "El usuario bloqueó el bot. Guardado como FAILED_DELIVERY.",
    "q.send_failed": "Error al enviar: {err}",
    "q.db_update_failed": "Enviado al usuario pero falló la actualización en la base de datos.",
    "q.answered": "✅ Pregunta #{qid} respondida",

    # --- Subscriptions & Payment ------------------------------------------- #
    "sm.title": "📜 Centro de Suscripciones y Pagos",
    "sm.desc": (
        "Explora suscripciones, pagos recientes, el registro de eventos de webhook "
        "y el último pago por usuario."
    ),
    "sm.btn_subscriptions": "📜 Suscripciones",
    "sm.btn_recent_payments": "💵 Pagos recientes",
    "sm.btn_webhook_log": "📡 Registro de webhook",
    "sm.btn_last_payment": "👤 Último pago / usuario",

    "sl.empty_title": "📜 Resumen de Gestión de Suscripciones",
    "sl.empty_body": "No se encontraron suscripciones.",
    "sl.empty_hint": "Las suscripciones activas y pasadas aparecerán aquí cuando los usuarios se suscriban.",
    "sl.header": "<b>Suscripciones</b> ({n})",

    "pay.empty_title": "💵 Resumen de Pagos Recientes",
    "pay.empty_body": "Aún no se ha registrado ningún pago.",
    "pay.empty_hint": "Los eventos de webhook de Stripe llenarán esta lista en cuanto los usuarios paguen.",
    "pay.header": "<b>Pagos recientes</b> ({n})",

    "wl.empty_title": "📡 Registro de Eventos de Webhook",
    "wl.empty_body": "Aún no se ha registrado ningún evento de webhook.",
    "wl.empty_hint": "Las entregas de Stripe y otros eventos de proveedores aparecerán aquí.",
    "wl.header": "<b>Registro de webhook / eventos</b> ({n})",

    "pp.empty_title": "👤 Último Pago por Usuario",
    "pp.empty_body": "Aún no hay pagos vinculados a ningún usuario.",
    "pp.empty_hint": "El pago más reciente de cada usuario se resumirá aquí.",
    "pp.header": "<b>Último pago por usuario</b> ({n} usuarios)",

    # Admin subscription readout header
    "sub.admin_header": "🛠 Vista de suscripción (admin) — usuario {user_id}",

    # --- System settings ---------------------------------------------------- #
    "sys.title": "⚙️ Resumen de Configuración del Sistema",
    "sys.desc": (
        "Vista de solo lectura de los valores de configuración con los que el bot "
        "está ejecutándose. Usa el panel de Render para cambiarlos."
    ),
    "sys.lbl_vip_lapse": "Retraso de eliminación por lapso VIP (s):",
    "sys.lbl_vip_sync": "Intervalo de sincronización VIP (s):",
    "sys.lbl_stripe_mode": "Modo de Stripe:",
    "sys.lbl_stripe_key_set": "Clave de Stripe configurada:",
    "sys.lbl_webhook_secret_set": "Secreto de webhook configurado:",
    "sys.btn_refresh": "🔄 Actualizar",
    "sys.btn_language": "🌐 Idioma del Administrador",

    # --- User export (Excel) ----------------------------------------------- #
    "export.section_title": "📊 Exportar Datos",
    "export.btn_active": "📗 Exportar Usuarios Activos",
    "export.btn_expired": "📕 Exportar Usuarios Expirados",
    "export.btn_grace": "⏳ Exportar Usuarios en Gracia",
    "export.btn_pending": "📄 Exportar Usuarios Pendientes",
    "export.btn_all": "📊 Exportar Todos los Usuarios",
    # Dataset names (used in the file caption + sheet title).
    "export.name_active": "Usuarios Activos",
    "export.name_expired": "Usuarios Expirados",
    "export.name_grace": "Usuarios en Periodo de Gracia",
    "export.name_pending": "Usuarios Pendientes de Aprobación",
    "export.name_all": "Todos los Usuarios",
    "export.generating": "Generando exportación…",
    "export.caption": "📊 {name} — {n} registro(s) exportado(s).",
    "export.empty": "Nada que exportar — esta lista ahora está vacía.",
    "export.failed": "❌ La exportación falló. Inténtalo de nuevo.",
    # Column headers
    "export.col_user_id": "ID de Usuario de Telegram",
    "export.col_username": "Nombre de Usuario",
    "export.col_full_name": "Nombre Completo",
    "export.col_status": "Estado",
    "export.col_sub_status": "Estado de Suscripción",
    "export.col_case_type": "Tipo de Caso",
    "export.col_created": "Fecha de Creación",
    "export.col_approved": "Fecha de Aprobación",

    # --- Admin language picker --------------------------------------------- #
    "lang.title": "🌐 Idioma del Administrador",
    "lang.desc": "Elige el idioma de la interfaz de administración. El inglés es el predeterminado.",
    "lang.prompt": "Selecciona un idioma abajo.",
    "lang.current": "Actual: {label}",
    "lang.changed": "Idioma actualizado.",
    "lang.menu_refreshed": "✅ Idioma del menú actualizado. Los botones de abajo ya están en el nuevo idioma.",

    # ======================================================================= #
    # Legacy command handlers (app/handlers/admin.py)
    # ======================================================================= #
    "cmd.not_authorized": "❌ No tienes autorización para usar este comando.",

    # Command palette ("/" menu) descriptions for the admin.
    "cmd_desc.start": "Abrir el panel de administración",
    "cmd_desc.help": "Ayuda de administrador",
    "cmd_desc.status": "Estado del administrador",
    "cmd_desc.language": "Cambiar idioma del administrador",
    "cmd_desc.pending": "Aprobaciones pendientes",
    "cmd_desc.users": "Listar usuarios",
    "cmd_desc.stats": "Estadísticas de usuarios",

    # Admin /status (admin never sees the user verification status flow).
    "cmd.admin_status_title": "👑 Estado del Administrador",
    "cmd.admin_status_body": (
        "Eres el administrador — acceso total, sin verificación ni aprobación.\n"
        "Usa los botones de sección de abajo para gestionar el bot."
    ),

    # /approve
    "cmd.approve_invalid_format": (
        "❌ Formato inválido. Usa: /approve [user_id]\n\nEjemplo: /approve 123456789"
    ),
    "cmd.approve_invalid_id": (
        "❌ ID de usuario inválido. Proporciona un ID de usuario numérico.\n\nEjemplo: /approve 123456789"
    ),
    "cmd.user_not_found": "❌ Usuario {user_id} no encontrado en la base de datos.",
    "cmd.approve_not_verified": "❌ El usuario {user_id} aún no ha sido verificado.",
    "cmd.approve_not_requested": "❌ El usuario {user_id} aún no ha solicitado acceso.",
    "cmd.approve_already": "✅ El usuario {user_id} ya está aprobado.",
    "cmd.approve_not_pending": "❌ El usuario {user_id} no está pendiente de aprobación.",
    "cmd.approve_failed": "❌ No se pudo aprobar al usuario. Inténtalo de nuevo.",
    "cmd.approve_success": (
        "✅ El usuario {user_id} ha sido aprobado.\n\n"
        "Fue notificado en chat privado. La invitación VIP se envía solo después "
        "de que tenga una suscripción activa (o gracia válida)."
    ),
    "cmd.approve_error": "❌ Ocurrió un error al procesar la aprobación.",
    "cmd.approve_not_pending_status": "❌ El usuario {user_id} no está pendiente de aprobación (estado: {status}).",

    # /reject
    "cmd.reject_invalid_format": (
        "❌ **Formato Inválido**\n\n"
        "Uso: `/reject [user_id] [reason]`\n\n"
        "Ejemplo: `/reject 123456789 Contenido inapropiado`\n\n"
        "El motivo es opcional"
    ),
    "cmd.reject_invalid_id": (
        "❌ **ID de Usuario Inválido**\n\n"
        "El ID de usuario debe ser un valor numérico.\n\n"
        "Ejemplo: `/reject 123456789`"
    ),
    "cmd.reject_user_not_found": "❌ **Usuario No Encontrado**\n\nUsuario {user_id} no encontrado en la base de datos.",
    "cmd.reject_already": "⚠️ **Ya Rechazado**\n\nEl usuario {user_id} ya está rechazado.",
    "cmd.reject_db_error": "❌ **Error de Base de Datos**\n\nNo se pudo actualizar el estado del usuario. Inténtalo de nuevo.",
    "cmd.reject_db_error_process": "❌ **Error de Base de Datos**\n\nNo se pudo procesar el rechazo. Inténtalo de nuevo.",
    "cmd.reject_system_error": "❌ **Error del Sistema**\n\nOcurrió un error inesperado. Inténtalo de nuevo.",
    "cmd.reject_success": (
        "✅ **Usuario Rechazado Correctamente**\n\n"
        "ID de Usuario: {user_id}\n"
        "Motivo: {reason}\n\n"
        "**Operaciones:**\n"
        "• Actualización de base de datos: ✅ Correcto\n"
        "• Notificación enviada: {notif}\n"
    ),
    "cmd.op_success": "✅ Correcto",
    "cmd.op_failed": "❌ Fallido",
    "cmd.reject_group_removal": "• Eliminación del grupo: {result}\n",
    "cmd.reject_group_skipped": "• Eliminación del grupo: ⏭ Omitida\n",
    "cmd.reject_db_error_cb": "❌ **Error de Base de Datos**\n\nNo se pudo rechazar al usuario {user_id}. Inténtalo de nuevo.",
    "cmd.cb_invalid_user_id": "❌ ID de usuario inválido en los datos de devolución",
    "cmd.cb_approve_error": "❌ Error al procesar la aprobación",
    "cmd.cb_reject_error": "❌ Error al procesar el rechazo",

    # /pending
    "cmd.pending_empty": (
        "<b>📋 Cola de Aprobación Pendiente</b>\n\n"
        "{sep}\n\n"
        "Actualmente no hay usuarios esperando aprobación.\n\n"
        "Las nuevas solicitudes de acceso aparecerán aquí en cuanto lleguen.\n\n"
        "{sep}"
    ),
    "cmd.pending_header": "📋 Usuarios Pendientes de Aprobación:\n\n",
    "cmd.pending_row": "🆔 ID de Usuario: {user_id}\n💡 Aprobar con: /approve {user_id}\n\n",
    "cmd.pending_error": "❌ Ocurrió un error al obtener los usuarios pendientes.",

    # /users
    "cmd.users_empty": (
        "<b>👥 Resumen de Gestión de Usuarios</b>\n\n"
        "{sep}\n\n"
        "Todavía no hay usuarios registrados en el sistema.\n\n"
        "Los usuarios aparecerán aquí en cuanto comiencen el registro.\n\n"
        "{sep}"
    ),
    "cmd.users_header": "👥 Lista de Todos los Usuarios:\n\n",
    "cmd.users_row": (
        "{role_emoji} **{first_name}**\n"
        "🆔 ID: `{telegram_id}`\n"
        "👤 Usuario: {username_display}\n"
        "🔷 Rol: {role_name}\n\n"
    ),
    "cmd.users_no_username": "Sin nombre de usuario",
    "cmd.role_new": "Usuario Nuevo",
    "cmd.role_verified": "Verificado",
    "cmd.role_pending": "Pendiente de Aprobación",
    "cmd.role_approved": "Aprobado",
    "cmd.role_unknown": "Desconocido",
    "cmd.users_error": "❌ Ocurrió un error al obtener la lista de usuarios.",

    # /stats
    "cmd.stats": (
        "📊 Estadísticas de Usuarios:\n\n"
        "🆕 Usuarios Nuevos: {new}\n"
        "✅ Usuarios Verificados: {verified}\n"
        "⏳ Pendientes de Aprobación: {pending}\n"
        "🎉 Usuarios Aprobados: {approved}\n\n"
        "📈 Total de Usuarios: {total}"
    ),
    "cmd.stats_error": "❌ Ocurrió un error al obtener las estadísticas.",

    # /sub_* commands
    "cmd.sub_status_usage": "Uso: /sub_status [user_id]",
    "cmd.sub_activate_usage": "Uso: /sub_activate [user_id]",
    "cmd.sub_expire_usage": "Uso: /sub_expire [user_id]",
    "cmd.sub_grace_usage": "Uso: /sub_grace [user_id] [grace_days]",
    "cmd.invalid_user_id_numeric": "user_id inválido (debe ser numérico).",
    "cmd.grace_days_numeric": "grace_days debe ser numérico.",
    "cmd.sub_activated": "✅ Activada.",
    "cmd.sub_activate_failed": "❌ Falló la activación (ver registros).",
    "cmd.sub_expired": "✅ Marcada como EXPIRED.",
    "cmd.sub_expire_failed": "❌ No hay suscripción que expirar.",
    "cmd.sub_grace_ok": "✅ Movida a GRACE.",
    "cmd.sub_grace_failed": "❌ Falló la transición a gracia (ver registros).",

    # /admin_help
    "cmd.admin_menu_btn_users": "📋 Mostrar Lista de Usuarios",
    "cmd.admin_menu_btn_pending": "⏳ Mostrar Usuarios Pendientes",
    "cmd.admin_menu_btn_stats": "📊 Mostrar Estadísticas",
    "cmd.admin_menu_btn_help": "❓ Ayuda de Administrador",
    "cmd.admin_menu_text": (
        "🔧 Menú de Administrador\n\n"
        "Comandos disponibles:\n"
        "/approve [user_id] - Aprobar usuarios pendientes\n"
        "/reject [user_id] [reason] - Rechazar usuarios pendientes\n"
        "/users - Mostrar todos los usuarios con detalles\n"
        "/pending - Mostrar todos los usuarios pendientes de aprobación\n"
        "/stats - Ver estadísticas de usuarios\n"
        "/simulate_payment [user_id] [success|failed|renew|cancel] - Simular evento de pago\n"
        "/simulate_subscription_expiry [user_id] - Simular expiración de suscripción\n"
        "/sub_status [user_id] - Resumen de suscripción + permisos\n"
        "/sub_activate [user_id] - Activar suscripción (capa de servicio)\n"
        "/sub_expire [user_id] - Forzar expiración de la última suscripción\n"
        "/sub_grace [user_id] [days] - Mover suscripción a gracia\n"
        "/admin_help - Mostrar este menú\n\n"
        "O usa los botones de abajo para acciones rápidas:"
    ),

    # admin /start welcome
    "cmd.admin_welcome": (
        "👑 **Bienvenido, Administrador**\n\n"
        "Estás aprobado automáticamente como administrador.\n\n"
        "🔧 **Funciones de Administrador Disponibles:**\n"
        "• `/approve [user_id]` - Aprobar usuarios pendientes\n"
        "• `/pending` - Ver usuarios pendientes\n"
        "• `/users` - Ver todos los usuarios\n"
        "• `/stats` - Ver estadísticas de usuarios\n"
        "• Moderación de mensajes del grupo\n"
        "• Reenvío y respuesta de preguntas\n\n"
        "📊 **Tu Estado:** APPROVED\n"
        "🎯 **Preguntas:** Ilimitadas\n\n"
        "¡Listo para gestionar el grupo VIP!"
    ),
    "cmd.admin_setup_error": (
        "❌ **Error de Configuración de Administrador**\n\n"
        "Hubo un error al configurar tu cuenta de administrador. Inténtalo de nuevo."
    ),

    # /retry
    "cmd.retry_invalid_command": (
        "❌ **Comando Inválido**\n\nUso: `/retry [question_id]`\n\nEjemplo: `/retry 123`"
    ),
    "cmd.retry_invalid_id": (
        "❌ **ID de Pregunta Inválido**\n\nEl ID de pregunta debe ser un número.\n\nEjemplo: `/retry 123`"
    ),
    "cmd.retry_not_found": (
        "❌ **Pregunta No Encontrada**\n\n"
        "Pregunta {question_id} no encontrada o no está en estado FAILED_DELIVERY."
    ),
    "cmd.retry_no_bot": "❌ Instancia del bot no disponible.",
    "cmd.retry_success": (
        "✅ **Reintento Exitoso**\n\n"
        "Pregunta {question_id} entregada correctamente al usuario {user_id}."
    ),
    "cmd.retry_partial": (
        "⚠️ **Éxito Parcial**\n\n"
        "Mensaje enviado al usuario pero falló la actualización del estado en la base de datos."
    ),
    "cmd.retry_failed": (
        "❌ **Reintento Fallido**\n\nNo se pudo entregar la pregunta {question_id} al usuario: {err}"
    ),
    "cmd.retry_error": "❌ Ocurrió un error al procesar el comando de reintento.",

    # /simulate_payment
    "cmd.sim_payment_invalid": (
        "❌ **Comando Inválido**\n\n"
        "Uso: `/simulate_payment [user_id] [success|failed|renew|cancel]`"
    ),
    "cmd.sim_user_id_numeric": "❌ El ID de usuario debe ser numérico.",
    "cmd.sim_action_invalid": "❌ La acción debe ser una de: success, failed, renew, cancel",
    "cmd.sim_payment_ok": "✅ Simulado `{event_type}` para el usuario `{user_id}`",
    "cmd.sim_payment_failed": "❌ Falló la simulación de `{event_type}` para el usuario `{user_id}`",

    # /simulate_subscription_expiry
    "cmd.sim_expiry_invalid": (
        "❌ **Comando Inválido**\n\nUso: `/simulate_subscription_expiry [user_id]`"
    ),
    "cmd.sim_expiry_ok": "✅ Expiración de suscripción simulada para el usuario `{user_id}`",
    "cmd.sim_expiry_failed": "❌ No se encontró suscripción activa para el usuario `{user_id}`",

    # /reset_user
    "cmd.reset_invalid_command": (
        "❌ **Comando Inválido**\n\n"
        "Uso: `/reset_user [telegram_user_id]`\n\n"
        "Ejemplo: `/reset_user 7285268952`"
    ),
    "cmd.reset_invalid_id": (
        "❌ **ID de Usuario Inválido**\n\nEl ID de usuario debe ser un número.\n\nEjemplo: `/reset_user 7285268952`"
    ),
    "cmd.reset_safety": "❌ **Error de Seguridad**\n\nNo se puede restablecer la cuenta del administrador.",
    "cmd.reset_user_not_found": "❌ **Usuario No Encontrado**\n\nUsuario {user_id} no encontrado en la base de datos.",
    "cmd.reset_success": (
        "✅ El usuario {user_id} fue eliminado completamente de la base de datos.\n\n"
        "Todas las preguntas, la suscripción y los pagos de este ID se eliminaron.\n"
        "Será tratado como un usuario completamente nuevo la próxima vez que envíe /start."
    ),
    "cmd.reset_failed": "❌ **Restablecimiento Fallido**\n\nNo se pudo restablecer al usuario {user_id}. Inténtalo de nuevo.",
    "cmd.reset_error": "❌ **Error de Restablecimiento**\n\nOcurrió un error al restablecer al usuario {user_id}: {err}",
    "cmd.reset_command_error": "❌ Ocurrió un error al procesar el comando de restablecimiento.",
}
