from core import *

ADV_FLOAT_FIELDS = {
    'referral_level_1_reward': 'Level 1 reward (₹)',
    'referral_level_2_reward': 'Level 2 reward (₹)',
    'referral_level_3_reward': 'Level 3 reward (₹)',
    'withdraw_bonus_tax_percent': 'Bonus withdraw tax %',
    'upi_gst_percent': 'UPI GST %',
    'inactivity_deduction_percent': 'Inactivity deduction %',
    'mines_house_edge': 'Mine house edge %',
    'mines_base_multiplier': 'Mine base multiplier',
    'mines_progressive_step': 'Mine progressive step',
    'mines_max_multiplier_cap': 'Mine max multiplier',
    'mines_bet_fee_percent': 'Mine bet fee %',
    'mines_winning_tax_percent': 'Mine winning tax %',
    'mines_gst_percent': 'Mine GST %',
    'mines_min_bet': 'Mine min bet (₹)',
    'mines_max_bet': 'Mine max bet (₹)',
    'mines_max_winnings_per_round': 'Mine max single win (₹)',
    'mines_daily_win_cap': 'Mine daily win cap (₹)',
    'mines_auto_cashout_default': 'Mine auto cashout default',
}

ADV_INT_FIELDS = {
    'min_refs_for_daily_bonus': 'Minimum referrals for daily bonus',
    'min_refs_for_redeem_code': 'Minimum referrals for redeem code',
    'inactivity_days': 'Inactivity days before deduction',
    'mines_grid_rows': 'Mine grid rows',
    'mines_grid_cols': 'Mine grid cols',
    'mines_min_count': 'Minimum mine count',
    'mines_max_count': 'Maximum mine count',
    'mines_cooldown_seconds': 'Mine cooldown seconds',
    'mines_daily_limit': 'Mine daily plays per user',
    'mines_hourly_limit': 'Mine hourly plays per user',
    'mines_force_cashout_after': 'Force cashout after safe picks',
    'mines_min_account_age_days': 'Minimum account age in days',
}

TOGGLE_FIELDS = {
    'referral_system_enabled': 'Referral system',
    'referral_level_1_enabled': 'Referral level 1',
    'referral_level_2_enabled': 'Referral level 2',
    'referral_level_3_enabled': 'Referral level 3',
    'referral_require_verification': 'Referral requires verification',
    'withdraw_bonus_tax_enabled': 'Withdraw bonus tax',
    'upi_gst_enabled': 'UPI GST',
    'games_enabled': 'Games',
    'games_show_history': 'Game history',
    'games_section_visible': 'Games section visibility',
    'mines_game_enabled': 'Mine game',
    'mines_allow_custom_mines': 'Mine custom mine count',
    'mines_fixed_mode_enabled': 'Fixed mine mode',
    'mines_force_safe_first_tile': 'Safe first tile',
    'mines_risk_indicator_enabled': 'Risk indicator',
    'mines_sound_enabled': 'Sound effects',
    'mines_manual_cashout_enabled': 'Manual cashout',
    'mines_auto_cashout_enabled': 'Auto cashout',
    'mines_cashout_confirmation': 'Cashout confirmation',
    'mines_user_choose_balance_source': 'User choose balance source',
    'mines_allow_bonus_balance': 'Use bonus balance',
    'mines_allow_referral_balance': 'Use referral balance',
    'mines_allow_gift_balance': 'Use gift balance',
    'mines_allow_main_balance': 'Use main balance',
    'mines_show_heatmap': 'Mine heatmap analytics',
    'mines_real_time_monitor_enabled': 'Real-time mine monitor',
    'mines_force_win_global': 'Global force win',
    'mines_force_loss_global': 'Global force loss',
}


def _bool_icon(value):
    return '🟢' if bool(value) else '🔴'


def _setting_btn(label, key):
    value = get_setting(key)
    return types.InlineKeyboardButton(f"{label}: {_bool_icon(value)}", callback_data=f"adv_toggle|{key}")


def admin_reply_label(key):
    return ADV_FLOAT_FIELDS.get(key) or ADV_INT_FIELDS.get(key) or TOGGLE_FIELDS.get(key) or key


@bot.message_handler(func=lambda m: m.text == "🧠 Advanced Settings" and is_admin(m.from_user.id))
def admin_advanced_settings(message):
    show_advanced_panel(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🎮 Game Control" and is_admin(m.from_user.id))
def admin_game_control(message):
    show_game_control_panel(message.chat.id)


def show_advanced_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Referral Engine", callback_data="adv_referral"),
        types.InlineKeyboardButton("💸 Economy & Tax", callback_data="adv_economy"),
    )
    markup.add(
        types.InlineKeyboardButton("🎮 Game Control", callback_data="adv_games"),
        types.InlineKeyboardButton("🤖 Automation", callback_data="adv_automation"),
    )
    markup.add(
        types.InlineKeyboardButton("📢 Announcements", callback_data="adv_announcements"),
        types.InlineKeyboardButton("📈 Mine Reports", callback_data="adv_reports"),
    )
    safe_send(
        chat_id,
        f"{pe('gear')} <b>Advanced Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{pe('info')} Full system controls for referral, tax, automation, announcements and Mine engine.\n"
        f"{pe('check')} All new controls are Railway-safe and stored in DB settings.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=markup,
    )


def show_game_control_panel(chat_id):
    rows = int(get_setting('mines_grid_rows') or 5)
    cols = int(get_setting('mines_grid_cols') or 5)
    mines_min = int(get_setting('mines_min_count') or 1)
    mines_max = int(get_setting('mines_max_count') or 5)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(_setting_btn('Mine Game', 'mines_game_enabled'), _setting_btn('Safe First Tile', 'mines_force_safe_first_tile'))
    markup.add(_setting_btn('Manual Cashout', 'mines_manual_cashout_enabled'), _setting_btn('Auto Cashout', 'mines_auto_cashout_enabled'))
    markup.add(_setting_btn('Global Force Win', 'mines_force_win_global'), _setting_btn('Global Force Loss', 'mines_force_loss_global'))
    markup.add(
        types.InlineKeyboardButton(f"Grid {rows}x{cols}", callback_data="adv_grid"),
        types.InlineKeyboardButton(f"Mines {mines_min}-{mines_max}", callback_data="adv_mine_range"),
    )
    markup.add(
        types.InlineKeyboardButton("💰 Payout Controls", callback_data="adv_mine_payout"),
        types.InlineKeyboardButton("🧪 Risk / Limits", callback_data="adv_mine_limits"),
    )
    markup.add(
        types.InlineKeyboardButton("🎨 UX / Theme", callback_data="adv_mine_ux"),
        types.InlineKeyboardButton("📊 Live Monitor", callback_data="adv_reports"),
    )
    safe_send(
        chat_id,
        f"{pe('game')} <b>Game Control Center</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Grid: <b>{rows}x{cols}</b>\n"
        f"Mine Range: <b>{mines_min} - {mines_max}</b>\n"
        f"Base Multiplier: <b>{float(get_setting('mines_base_multiplier') or 1.12):.2f}x</b>\n"
        f"Progressive Step: <b>{float(get_setting('mines_progressive_step') or 0.17):.2f}x</b>\n"
        f"House Edge: <b>{float(get_setting('mines_house_edge') or 3):.2f}%</b>\n"
        f"Max Win / Round: <b>₹{float(get_setting('mines_max_winnings_per_round') or 100):.2f}</b>\n"
        f"Daily Cap: <b>₹{float(get_setting('mines_daily_win_cap') or 500):.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == 'adv_referral')
def adv_referral(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(_setting_btn('Referral System', 'referral_system_enabled'), _setting_btn('Need Verification', 'referral_require_verification'))
    markup.add(_setting_btn('Level 1', 'referral_level_1_enabled'), _setting_btn('Level 2', 'referral_level_2_enabled'))
    markup.add(_setting_btn('Level 3', 'referral_level_3_enabled'))
    markup.add(
        types.InlineKeyboardButton(f"L1 ₹{float(get_setting('referral_level_1_reward') or 0):.2f}", callback_data='adv_float|referral_level_1_reward'),
        types.InlineKeyboardButton(f"L2 ₹{float(get_setting('referral_level_2_reward') or 0):.2f}", callback_data='adv_float|referral_level_2_reward'),
    )
    markup.add(
        types.InlineKeyboardButton(f"L3 ₹{float(get_setting('referral_level_3_reward') or 0):.2f}", callback_data='adv_float|referral_level_3_reward'),
        types.InlineKeyboardButton(f"Daily Bonus Req {int(get_setting('min_refs_for_daily_bonus') or 0)}", callback_data='adv_int|min_refs_for_daily_bonus'),
    )
    markup.add(types.InlineKeyboardButton(f"Redeem Req {int(get_setting('min_refs_for_redeem_code') or 0)}", callback_data='adv_int|min_refs_for_redeem_code'))
    safe_send(call.message.chat.id, f"{pe('people')} <b>Referral Controls</b>\nUse the buttons below to toggle levels and edit rewards.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_economy')
def adv_economy(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(_setting_btn('Withdraw Bonus Tax', 'withdraw_bonus_tax_enabled'), _setting_btn('UPI GST', 'upi_gst_enabled'))
    markup.add(
        types.InlineKeyboardButton(f"Bonus Tax {float(get_setting('withdraw_bonus_tax_percent') or 0):.2f}%", callback_data='adv_float|withdraw_bonus_tax_percent'),
        types.InlineKeyboardButton(f"UPI GST {float(get_setting('upi_gst_percent') or 0):.2f}%", callback_data='adv_float|upi_gst_percent'),
    )
    markup.add(
        types.InlineKeyboardButton(f"Inactivity Days {int(get_setting('inactivity_days') or 0)}", callback_data='adv_int|inactivity_days'),
        types.InlineKeyboardButton(f"Inactivity Deduct {float(get_setting('inactivity_deduction_percent') or 0):.2f}%", callback_data='adv_float|inactivity_deduction_percent'),
    )
    safe_send(call.message.chat.id, f"{pe('money')} <b>Economy / Tax Controls</b>\nBalance deductions, withdraw tax and inactivity penalties are controlled here.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_games')
def adv_games(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    show_game_control_panel(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_automation')
def adv_automation(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(_setting_btn('Game History', 'games_show_history'), _setting_btn('Risk Indicator', 'mines_risk_indicator_enabled'))
    markup.add(_setting_btn('Realtime Monitor', 'mines_real_time_monitor_enabled'), _setting_btn('Heatmap', 'mines_show_heatmap'))
    markup.add(_setting_btn('Sound FX', 'mines_sound_enabled'), _setting_btn('Cashout Confirm', 'mines_cashout_confirmation'))
    safe_send(call.message.chat.id, f"{pe('rocket')} <b>Automation / UX Toggles</b>\nThese controls affect automation, analytics and user-facing Mine behavior.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_announcements')
def adv_announcements(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    set_state(call.from_user.id, 'admin_set_announcement_text')
    safe_send(call.message.chat.id, f"{pe('megaphone')} Send the announcement text. It will be stored in settings and can be surfaced in the web app.")


@bot.callback_query_handler(func=lambda call: call.data == 'adv_reports')
def adv_reports(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    stats = db_execute("SELECT COUNT(*) c, COALESCE(SUM(bet_amount),0) bets, COALESCE(SUM(reward_amount),0) rewards FROM game_history WHERE game_key='mines'", fetchone=True) or {'c': 0, 'bets': 0, 'rewards': 0}
    active = db_execute("SELECT COUNT(*) c FROM mine_games WHERE status='active'", fetchone=True) or {'c': 0}
    safe_send(call.message.chat.id, f"{pe('chart')} <b>Mine Reports</b>\n\nSessions: <b>{stats['c']}</b>\nTotal Bets: <b>₹{float(stats['bets'] or 0):.2f}</b>\nTotal Rewards: <b>₹{float(stats['rewards'] or 0):.2f}</b>\nActive Sessions: <b>{active['c']}</b>")


@bot.callback_query_handler(func=lambda call: call.data == 'adv_grid')
def adv_grid(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    set_state(call.from_user.id, 'admin_set_grid_size')
    safe_send(call.message.chat.id, f"{pe('pencil')} Send grid size as <code>rows x cols</code>. Example: <code>5x5</code>")


@bot.callback_query_handler(func=lambda call: call.data == 'adv_mine_range')
def adv_mine_range(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    set_state(call.from_user.id, 'admin_set_mine_range')
    safe_send(call.message.chat.id, f"{pe('pencil')} Send mine range as <code>min-max</code>. Example: <code>1-10</code>")


@bot.callback_query_handler(func=lambda call: call.data == 'adv_mine_payout')
def adv_mine_payout(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key in ['mines_base_multiplier', 'mines_progressive_step', 'mines_max_multiplier_cap', 'mines_bet_fee_percent', 'mines_winning_tax_percent', 'mines_gst_percent', 'mines_house_edge']:
        markup.add(types.InlineKeyboardButton(f"{admin_reply_label(key)}", callback_data=f"adv_float|{key}"))
    safe_send(call.message.chat.id, f"{pe('coins')} <b>Mine Payout Controls</b>\nChoose a field to edit.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_mine_limits')
def adv_mine_limits(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key in ['mines_min_bet', 'mines_max_bet', 'mines_cooldown_seconds', 'mines_daily_limit', 'mines_hourly_limit', 'mines_force_cashout_after', 'mines_max_winnings_per_round', 'mines_daily_win_cap', 'mines_min_account_age_days']:
        cb = f"adv_float|{key}" if key in ADV_FLOAT_FIELDS else f"adv_int|{key}"
        markup.add(types.InlineKeyboardButton(admin_reply_label(key), callback_data=cb))
    safe_send(call.message.chat.id, f"{pe('shield')} <b>Mine Limits / Restrictions</b>", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'adv_mine_ux')
def adv_mine_ux(call):
    if not is_admin(call.from_user.id):
        return
    safe_answer(call)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key in ['mines_risk_indicator_enabled', 'mines_sound_enabled', 'mines_cashout_confirmation', 'mines_user_choose_balance_source', 'mines_allow_main_balance', 'mines_allow_bonus_balance', 'mines_allow_referral_balance', 'mines_allow_gift_balance']:
        markup.add(_setting_btn(admin_reply_label(key), key))
    safe_send(call.message.chat.id, f"{pe('sparkle')} <b>Mine UX / Balance Source Controls</b>", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adv_toggle|'))
def adv_toggle(call):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split('|', 1)[1]
    current = bool(get_setting(key))
    set_setting(key, not current)
    log_admin_action(call.from_user.id, 'toggle_setting', f'{key}={not current}')
    safe_answer(call, f"{admin_reply_label(key)} {'enabled' if not current else 'disabled'}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('adv_float|'))
def adv_float(call):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split('|', 1)[1]
    safe_answer(call)
    set_state(call.from_user.id, f'admin_set_float|{key}')
    safe_send(call.message.chat.id, f"{pe('pencil')} Enter {admin_reply_label(key)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('adv_int|'))
def adv_int(call):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split('|', 1)[1]
    safe_answer(call)
    set_state(call.from_user.id, f'admin_set_int|{key}')
    safe_send(call.message.chat.id, f"{pe('pencil')} Enter {admin_reply_label(key)}")
