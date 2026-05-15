"""Spanish locale."""

MESSAGES = {
    # ===== Language picker =====
    "lang.picker_first_time": "🌐 ¡Bienvenido! Por favor, elige tu idioma:",
    "lang.picker_change": "🌐 Selecciona un idioma:",
    "lang.set_confirmation": "✅ Idioma cambiado a Español.",

    # ===== Buttons =====
    "btn.verify": "✅ Verificar",
    "btn.check_status": "📊 Ver estado",
    "btn.help": "❓ Ayuda",
    "btn.request_access": "🔑 Solicitar acceso",
    "btn.join_vip": "🎉 Unirse al grupo VIP",
    "btn.subscription": "📊 Suscripción",

    # ===== Verify =====
    "verify.welcome_new": (
        "👋 ¡Bienvenido a AskBot!\n\n"
        "Para comenzar, verifica tu cuenta pulsando el botón de abajo."
    ),
    "verify.welcome_verified": (
        "✅ ¡Estás verificado!\n\n"
        "Ahora puedes solicitar acceso al grupo VIP pulsando el botón de abajo."
    ),
    "verify.welcome_pending": (
        "⏳ Tu solicitud de acceso está siendo revisada.\n\n"
        "Espera a que un administrador la apruebe. "
        "Te notificaremos cuando haya una decisión."
    ),
    "verify.welcome_approved_vip": (
        "Estás aprobado y tu suscripción está activa.\n\n"
        "Usa el botón de abajo para abrir la invitación al grupo VIP."
    ),
    "verify.welcome_approved_no_sub": (
        "Estás aprobado. Activa una suscripción para recibir la invitación al grupo VIP.\n\n"
        "Usa /subscription y /subscribe (o /renew) en el chat privado con este bot."
    ),
    "verify.complete": (
        "✅ ¡Verificación completa!\n\n"
        "Ahora puedes solicitar acceso al grupo VIP pulsando el botón de abajo."
    ),
    "verify.alert_already_verified": "❌ ¡Ya estás verificado!",
    "verify.alert_success": "✅ ¡Verificado correctamente!",

    # ===== Status =====
    "status.not_registered_callback": (
        "📊 Tu estado actual: ❓ No registrado\n\n"
        "Aún no has iniciado el proceso de verificación.\n\n"
        "👉 Pulsa el botón '✅ Verificar' para comenzar el registro."
    ),
    "status.not_registered_dm": (
        "📊 Tu estado actual: ❓ No registrado\n\n"
        "Aún no has iniciado el proceso de verificación.\n\n"
        "👉 Envía /start para comenzar el registro."
    ),
    "status.label": "📊 Tu estado actual: {status}",
    "status.new": "🆕 Nuevo usuario - Verifica tu cuenta",
    "status.verified": "✅ Verificado - Puedes solicitar acceso",
    "status.pending": "⏳ Aprobación pendiente - Tu solicitud está en revisión",
    "status.approved": "🎉 Aprobado - Tienes acceso al grupo VIP",
    "status.rejected": "❌ Rechazado - Tu solicitud ha sido denegada",
    "status.unknown": "❓ Estado desconocido",
    "status.vip_active": "\n💳 Acceso VIP: Activo",
    "status.vip_inactive": "\n💳 Acceso VIP: Inactivo (se requiere suscripción)",
    "status.billing_link": "\n\n📎 Facturación y acceso: /subscription",

    # ===== Help =====
    "help.title": "🤖 Ayuda de AskBot\n\n",
    "help.new": (
        "Comandos disponibles:\n"
        "/start - Iniciar verificación\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/status - Ver tu estado actual\n"
        "/language - Cambiar idioma\n\n"
        "¡Pulsa el botón 'Verificar' para comenzar!"
    ),
    "help.verified": (
        "Comandos disponibles:\n"
        "/start - Mostrar opción de solicitar acceso\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/status - Ver tu estado actual\n"
        "/language - Cambiar idioma\n\n"
        "¡Pulsa el botón 'Solicitar acceso' para continuar!"
    ),
    "help.pending": (
        "Comandos disponibles:\n"
        "/start - Mostrar estado pendiente\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/status - Ver tu estado actual\n"
        "/language - Cambiar idioma\n\n"
        "Tu solicitud está en revisión. Espera la aprobación del administrador."
    ),
    "help.approved_with_vip": (
        "Comandos disponibles:\n"
        "/start - Mostrar estado aprobado\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/status - Ver tu estado actual\n"
        "/language - Cambiar idioma\n\n"
        "¡Tienes acceso al grupo VIP! Revisa tus mensajes para el enlace de invitación."
    ),
    "help.approved_billing": (
        "Comandos disponibles:\n"
        "/start - Mostrar estado aprobado\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/status - Ver tu estado actual\n"
        "/language - Cambiar idioma\n\n"
        "Estás aprobado. Tras activar una suscripción, recibirás la invitación VIP "
        "en chat privado. Usa /subscription."
    ),

    # ===== Access =====
    "access.alert_cannot_request": "❌ ¡No puedes solicitar acceso en esta etapa!",
    "access.alert_already_pending": "⏳ ¡Tu solicitud ya está en revisión!",
    "access.submitted": (
        "📝 ¡Tu solicitud de acceso ha sido enviada!\n\n"
        "⏳ Tu solicitud está en revisión. "
        "Un administrador la revisará y te notificará cuando haya una decisión.\n\n"
        "Por favor, ten paciencia - esto suele tardar algunas horas."
    ),
    "access.alert_submitted": "✅ ¡Solicitud enviada!",

    # ===== Questions =====
    "q.access_required_status": (
        "❌ Se requiere acceso\n\n"
        "Tu estado actual: {status}\n\n"
        "Necesitas estar aprobado para enviar preguntas.\n"
        "Inicia la verificación enviando /start"
    ),
    "q.subscription_inactive": (
        "❌ Tu suscripción está inactiva o ha expirado.\n"
        "Usa /renew para restaurar el acceso."
    ),
    "q.empty": "❌ Pregunta vacía\n\nEnvía una pregunta significativa.",
    "q.too_short": (
        "❌ Pregunta demasiado corta\n\n"
        "Envía una pregunta más detallada (al menos 3 caracteres)."
    ),
    "q.invalid": "❌ Pregunta no válida\n\nEnvía una pregunta significativa.",
    "q.cooldown": "⏳ Por favor espera\n\nEspera unos segundos antes de enviar otra pregunta.",
    "q.duplicate": "⚠️ Pregunta duplicada\n\nYa enviaste esta pregunta recientemente.",
    "q.limit_reached": (
        "❌ Límite de preguntas alcanzado\n\n"
        "Has usado tu límite diario de {limit} preguntas.\n\n"
        "El contador se restablecerá mañana. Inténtalo de nuevo entonces."
    ),
    "q.access_required_simple": (
        "❌ Se requiere acceso\n\n"
        "Necesitas estar aprobado para enviar preguntas.\n\n"
        "Inicia la verificación enviando /start"
    ),
    "q.system_error": (
        "❌ Error del sistema\n\n"
        "Lo sentimos, hubo un error procesando tu pregunta. Inténtalo más tarde."
    ),
    "q.system_error_user_not_found": "❌ Error del sistema\n\nUsuario no encontrado. Inténtalo de nuevo.",
    "q.system_error_generic": (
        "❌ Error del sistema\n\n"
        "Hubo un error procesando tu pregunta. Inténtalo de nuevo."
    ),
    "q.received": (
        "✅ Pregunta recibida\n\n"
        "Tu pregunta ha sido enviada al administrador.\n\n"
        "📊 Preguntas restantes hoy: {remaining}/{limit}\n\n"
        "Recibirás respuesta lo antes posible."
    ),
    "q.error_generic": "❌ Error\n\nHubo un error procesando tu pregunta. Inténtalo de nuevo.",
    "q.error_forwarding": (
        "❌ Error\n\n"
        "Tu pregunta fue recibida pero hubo un error al reenviarla. Inténtalo de nuevo."
    ),
    "q.text_only": (
        "❌ Solo texto\n\n"
        "Envía tus preguntas solo como mensajes de texto.\n\n"
        "Imágenes, archivos y otro contenido no son compatibles por ahora."
    ),
    "q.admin_response": (
        "📨 Respuesta del administrador\n\n"
        "❓ Tu pregunta:\n{question}\n\n"
        "💬 Respuesta:\n{reply}\n\n"
        "---\n"
        "Esta es una respuesta a tu pregunta. Puedes responder a este mensaje si necesitas aclaración."
    ),

    # ===== Subscription commands =====
    "sub.cmd_not_approved": (
        "Necesitas una cuenta aprobada antes de suscribirte.\n"
        "Usa /start para continuar la inscripción."
    ),
    "sub.cmd_mock_success": (
        "✅ Pago simulado aplicado. Tu suscripción se ha actualizado.\n"
        "Usa /subscription para ver los detalles."
    ),
    "sub.cmd_mock_failed": (
        "❌ La activación simulada falló. Inténtalo de nuevo o contacta a un administrador."
    ),

    # ===== Subscription readout =====
    "sub.readout_title": "📋 Suscripción",
    "sub.readout_account_status": "• Estado de la cuenta: {status}",
    "sub.readout_sub_state": "• Estado de la suscripción: {state}",
    "sub.readout_billing_mode": "• Modo de facturación: {mode}",
    "sub.readout_plan": "• Plan: {plan}",
    "sub.readout_period_end": "• Fin del período: {date}",
    "sub.readout_grace_until": "• Período de gracia hasta: {date}",
    "sub.readout_can_ask": "• Puedes hacer preguntas: {yes_no}",
    "sub.readout_access_detail": "• Detalle de acceso: {reason}",
    "sub.readout_yes": "Sí",
    "sub.readout_no": "No",
    "sub.readout_dash": "—",
    "sub.next_good_to_go": "✅ Todo listo. Usa /status cuando quieras.",
    "sub.next_complete_onboarding": "➡️ Completa la inscripción: /start",
    "sub.next_mock_subscribe": (
        "➡️ Prueba /subscribe para activar (simulado), o consulta a un administrador si necesitas ayuda."
    ),
    "sub.next_not_configured": (
        "➡️ La facturación aún no está activa. Atento a las novedades de los administradores."
    ),
    "sub.next_use_renew": (
        "➡️ Usa /renew cuando el pago esté disponible, o contacta con soporte."
    ),
    "sub.placeholder_msg": (
        "💳 Suscribirse\n\n"
        "El pago en línea aún no está habilitado. "
        "Podrás renovar aquí cuando la facturación esté activa.\n\n"
        "Si necesitas acceso urgente, contacta con un administrador."
    ),

    # ===== Persistent reply-keyboard menu =====
    "menu.btn_check_status": "📊 Estado de aprobación",
    "menu.btn_subscription": "💳 Suscripción",
    "menu.btn_change_language": "🌐 Cambiar idioma",
    "menu.installed": "📋 Usa el menú de abajo para navegar.",

    # ===== VIP invite =====
    "vip.invite": (
        "🎉 Tu suscripción está activa.\n\n"
        "Puedes unirte al grupo VIP con este enlace de invitación:\n\n"
        "{link}\n\n"
        "¡Bienvenido a la comunidad!"
    ),

    # ===== Admin → user notifications =====
    "admin.user_approved": (
        "🎉 Tu solicitud de acceso fue aprobada.\n\n"
        "Usa /subscription para ver el estado de tu facturación, y /subscribe o /renew "
        "para activar un plan cuando esté disponible.\n\n"
        "Recibirás un mensaje privado independiente con el enlace de invitación al grupo VIP "
        "una vez que tu suscripción esté activa (incluyendo un período de gracia válido)."
    ),
    "admin.user_rejected": (
        "❌ Solicitud de acceso rechazada\n\n"
        "Tu solicitud de acceso al grupo VIP ha sido denegada.\n\n"
        "Motivo: {reason}\n\n"
        "Si crees que esto es un error, por favor contacta a un administrador.\n\n"
        "Puedes enviar una nueva solicitud después de resolver el problema."
    ),

    # ===== Group moderation private DMs =====
    "group.private_subscription_required": (
        "Tu mensaje en el grupo VIP fue eliminado (solo anuncios).\n\n"
        "Necesitas una suscripción activa para reenviar preguntas desde el grupo. "
        "Usa /subscription para ver el estado, y luego /subscribe o /renew cuando seas elegible."
    ),
    "group.private_redirect_unapproved": (
        "Tu mensaje en el grupo VIP fue eliminado para mantener el canal limpio.\n\n"
        "Por favor, usa el chat privado con este bot para continuar la inscripción o hacer preguntas "
        "una vez que estés aprobado y suscrito."
    ),
    "group.forward_offer": (
        "Tu mensaje en el grupo VIP fue eliminado (solo anuncios).\n\n"
        "¿Quieres enviar esta pregunta al administrador en su lugar?\n\n"
        "—\n{preview}"
    ),
    "group.non_text_notice": (
        "Tu publicación en el grupo VIP fue eliminada. Solo se puede reenviar texto como pregunta.\n\n"
        "Envía tu pregunta en chat privado con este bot si necesitas ayuda."
    ),
    "group.btn_yes": "Sí",
    "group.btn_no": "No",
    "group.offer_cancelled_toast": "Cancelado",
    "group.offer_expired": (
        "Esa oferta expiró. Por favor, envía tu pregunta de nuevo desde el grupo o en chat privado."
    ),
}
