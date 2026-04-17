import os
import json
import uuid
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import request, jsonify, render_template
from anticheat import create_verification_app

PORT = int(os.environ.get("PORT", 8000))
DB_PATH = os.environ.get("DB_PATH", "/data/bot_database.db")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "NeturalPredictorbot")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
app = create_verification_app(DB_PATH=DB_PATH, BOT_USERNAME=BOT_USERNAME)

MINE_DEFAULTS = {
    'games_enabled': True,
    'mines_game_enabled': True,
    'global_announcement_text': '',
    'games_show_history': True,
    'mines_grid_rows': 5,
    'mines_grid_cols': 5,
    'mines_min_count': 1,
    'mines_max_count': 10,
    'mines_allow_custom_mines': True,
    'mines_fixed_mode_enabled': False,
    'mines_fixed_mine_count': 3,
    'mines_force_safe_first_tile': True,
    'mines_base_multiplier': 1.12,
    'mines_progressive_step': 0.17,
    'mines_max_multiplier_cap': 100.0,
    'mines_house_edge': 3.0,
    'mines_bet_fee_percent': 0.0,
    'mines_winning_tax_percent': 0.0,
    'mines_gst_percent': 0.0,
    'mines_min_bet': 1.0,
    'mines_max_bet': 50.0,
    'mines_cooldown_seconds': 15,
    'mines_daily_limit': 50,
    'mines_hourly_limit': 20,
    'mines_max_winnings_per_round': 100.0,
    'mines_daily_win_cap': 500.0,
    'mines_manual_cashout_enabled': True,
    'mines_auto_cashout_enabled': False,
    'mines_auto_cashout_default': 0.0,
    'mines_cashout_confirmation': False,
    'mines_force_cashout_after': 0,
    'mines_risk_indicator_enabled': True,
    'mines_sound_enabled': True,
    'mines_user_choose_balance_source': True,
    'mines_allow_main_balance': True,
    'mines_allow_bonus_balance': True,
    'mines_allow_referral_balance': True,
    'mines_allow_gift_balance': True,
    'mines_show_heatmap': True,
    'mines_real_time_monitor_enabled': True,
    'mines_force_win_global': False,
    'mines_force_loss_global': False,
    'mines_min_account_age_days': 0,
}


def _db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _json_load(value, default=None):
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default if default is not None else value


def _get_setting(cur, key, default=None):
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    if not row:
        return MINE_DEFAULTS.get(key, default)
    return _json_load(row[0], MINE_DEFAULTS.get(key, default))


def _ensure_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mine_games (
            game_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            grid_rows INTEGER NOT NULL DEFAULT 5,
            grid_cols INTEGER NOT NULL DEFAULT 5,
            bet_amount REAL NOT NULL,
            balance_source TEXT DEFAULT 'balance',
            mine_count INTEGER NOT NULL,
            mine_positions TEXT NOT NULL,
            revealed_tiles TEXT DEFAULT '[]',
            safe_picks INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            multiplier REAL DEFAULT 1.0,
            gross_payout REAL DEFAULT 0.0,
            net_payout REAL DEFAULT 0.0,
            bet_fee REAL DEFAULT 0.0,
            winning_tax REAL DEFAULT 0.0,
            gst_amount REAL DEFAULT 0.0,
            current_risk REAL DEFAULT 0.0,
            seed_used TEXT DEFAULT '',
            force_mode TEXT DEFAULT 'auto',
            auto_cashout_multiplier REAL DEFAULT 0.0,
            forced_cashout_after INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            ended_at TEXT,
            meta_json TEXT DEFAULT '{}'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_key TEXT,
            bet_amount REAL DEFAULT 0,
            reward_amount REAL DEFAULT 0,
            outcome TEXT,
            round_meta TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mine_tile_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            game_id TEXT DEFAULT '',
            tile_index INTEGER DEFAULT 0,
            was_mine INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ''
        )
        """
    )
    for stmt in [
        "ALTER TABLE users ADD COLUMN bonus_balance REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN referral_balance REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN gift_balance REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN game_balance REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0",
    ]:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass


def _user_row(cur, user_id):
    cur.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),))
    return cur.fetchone()


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _count_today(cur, user_id):
    start = datetime.now().strftime('%Y-%m-%d 00:00:00')
    cur.execute("SELECT COUNT(*) c FROM game_history WHERE user_id=? AND game_key='mines' AND created_at>=?", (user_id, start))
    return int((cur.fetchone() or {'c': 0})['c'])


def _count_last_hour(cur, user_id):
    cutoff = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("SELECT COUNT(*) c FROM game_history WHERE user_id=? AND game_key='mines' AND created_at>=?", (user_id, cutoff))
    return int((cur.fetchone() or {'c': 0})['c'])


def _daily_winnings(cur, user_id):
    start = datetime.now().strftime('%Y-%m-%d 00:00:00')
    cur.execute("SELECT COALESCE(SUM(reward_amount),0) r FROM game_history WHERE user_id=? AND game_key='mines' AND outcome='win' AND created_at>=?", (user_id, start))
    return float((cur.fetchone() or {'r': 0})['r'] or 0)


def _last_finished_game(cur, user_id):
    cur.execute("SELECT created_at FROM game_history WHERE user_id=? AND game_key='mines' ORDER BY id DESC LIMIT 1", (user_id,))
    return cur.fetchone()


def _settings_blob(cur):
    data = {k: _get_setting(cur, k, v) for k, v in MINE_DEFAULTS.items()}
    rows, cols = int(data['mines_grid_rows']), int(data['mines_grid_cols'])
    total = rows * cols
    data['tile_count'] = total
    data['allowed_balance_sources'] = [
        src for src, allowed in [
            ('balance', data['mines_allow_main_balance']),
            ('bonus_balance', data['mines_allow_bonus_balance']),
            ('referral_balance', data['mines_allow_referral_balance']),
            ('gift_balance', data['mines_allow_gift_balance']),
        ] if allowed
    ]
    data['mines_max_count'] = min(int(data['mines_max_count']), max(1, total - 1))
    data['mines_min_count'] = max(1, min(int(data['mines_min_count']), data['mines_max_count']))
    return data


def _calc_multiplier(revealed_count, mine_count, total_tiles, cfg):
    if revealed_count <= 0:
        return 1.0
    base = float(cfg['mines_base_multiplier'])
    step = float(cfg['mines_progressive_step'])
    cap = float(cfg['mines_max_multiplier_cap'])
    edge_factor = max(0.0, 1.0 - float(cfg['mines_house_edge']) / 100.0)
    risk_boost = 1.0 + (mine_count / max(1, total_tiles)) * 0.75
    mult = (base + (revealed_count - 1) * step * risk_boost) * edge_factor
    return round(max(1.0, min(cap, mult)), 4)


def _risk_value(revealed_count, mine_count, total_tiles):
    remaining_tiles = max(1, total_tiles - revealed_count)
    remaining_mines = mine_count
    return round(min(100.0, (remaining_mines / remaining_tiles) * 100), 2)


def _pick_mines(total_tiles, mine_count, first_safe_tile=None, force_mode='auto'):
    idx = list(range(total_tiles))
    if first_safe_tile is not None and first_safe_tile in idx:
        idx.remove(first_safe_tile)
    random.shuffle(idx)
    mines = set(idx[:mine_count])
    if force_mode == 'force_loss' and first_safe_tile is not None:
        mines = set(list(mines)[:max(0, mine_count - 1)])
        lose_tile = (first_safe_tile + 1) % total_tiles
        if lose_tile == first_safe_tile:
            lose_tile = (lose_tile + 1) % total_tiles
        mines.add(lose_tile)
        while len(mines) < mine_count:
            mines.add(random.choice([i for i in range(total_tiles) if i != first_safe_tile]))
    return sorted(mines)


def _get_balance(user, source):
    return round(float(user[source] or 0), 2)


def _set_balance(cur, user_id, source, new_balance):
    cur.execute(f"UPDATE users SET {source}=? WHERE user_id=?", (round(float(new_balance), 2), user_id))


def _credit_win(cur, user, source, net_payout):
    cur.execute(f"UPDATE users SET {source}={source}+?, total_earned=total_earned+? WHERE user_id=?", (net_payout, max(0, net_payout), user['user_id']))


def _balances_dict(user):
    return {
        'balance': round(float(user['balance'] or 0), 2),
        'bonus_balance': round(float(user['bonus_balance'] or 0), 2),
        'referral_balance': round(float(user['referral_balance'] or 0), 2),
        'gift_balance': round(float(user['gift_balance'] or 0), 2),
    }


@app.route('/debug')
def debug_info():
    return {'status': 'running', 'db_path': DB_PATH, 'bot': BOT_USERNAME}


@app.route('/ping')
def ping():
    return 'pong'


@app.route('/mine')
@app.route('/mine/')
@app.route('/mines')
@app.route('/mines/')
def mine_page():
    uid = request.args.get('uid', '0')
    return render_template('mine.html', uid=uid, bot_username=BOT_USERNAME)


@app.route('/api/mine/config')
def api_mine_config():
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    cfg = _settings_blob(cur)
    announcement = cfg.get('global_announcement_text') or ''
    conn.close()
    return jsonify({'ok': True, 'config': cfg, 'announcement': announcement})


@app.route('/api/mine/me')
def api_mine_me():
    user_id = int(request.args.get('uid') or request.args.get('user_id') or 0)
    if user_id <= 0:
        return jsonify({'ok': False, 'error': 'Invalid user'}), 400
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    user = _user_row(cur, user_id)
    cfg = _settings_blob(cur)
    conn.close()
    if not user:
        return jsonify({'ok': False, 'error': 'User not found'}), 404
    return jsonify({
        'ok': True,
        'user_id': user_id,
        'balances': _balances_dict(user),
        'games_enabled': bool(cfg['games_enabled']),
        'mines_game_enabled': bool(cfg['mines_game_enabled']),
        'min_bet': float(cfg['mines_min_bet']),
        'max_bet': float(cfg['mines_max_bet']),
        'config': cfg,
    })


@app.route('/api/mine/start', methods=['POST'])
def api_mine_start():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get('uid') or data.get('user_id') or 0)
    bet = round(float(data.get('bet') or 0), 2)
    mine_count = int(data.get('mines') or 3)
    balance_source = str(data.get('balance_source') or 'balance').strip()
    auto_cashout_multiplier = round(float(data.get('auto_cashout_multiplier') or 0), 2)
    if user_id <= 0:
        return jsonify({'ok': False, 'error': 'Invalid user'}), 400

    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    user = _user_row(cur, user_id)
    cfg = _settings_blob(cur)
    if not user:
        conn.close(); return jsonify({'ok': False, 'error': 'User not found'}), 404
    if int(user['banned'] or 0) == 1:
        conn.close(); return jsonify({'ok': False, 'error': 'User is blocked'}), 403
    if not bool(cfg['games_enabled']) or not bool(cfg['mines_game_enabled']):
        conn.close(); return jsonify({'ok': False, 'error': 'Game disabled by admin'}), 400
    if balance_source not in cfg['allowed_balance_sources']:
        conn.close(); return jsonify({'ok': False, 'error': 'Selected balance source is disabled'}), 400
    if bet < float(cfg['mines_min_bet']) or bet > float(cfg['mines_max_bet']):
        conn.close(); return jsonify({'ok': False, 'error': f"Bet must be between ₹{cfg['mines_min_bet']} and ₹{cfg['mines_max_bet']}"}), 400
    total_tiles = int(cfg['tile_count'])
    if cfg['mines_fixed_mode_enabled'] or not bool(cfg['mines_allow_custom_mines']):
        mine_count = int(cfg['mines_fixed_mine_count'])
    if mine_count < int(cfg['mines_min_count']) or mine_count > int(cfg['mines_max_count']) or mine_count >= total_tiles:
        conn.close(); return jsonify({'ok': False, 'error': 'Invalid mine count'}), 400
    if _get_balance(user, balance_source) < bet:
        conn.close(); return jsonify({'ok': False, 'error': 'Insufficient selected balance'}), 400

    min_account_age = int(cfg['mines_min_account_age_days'])
    joined_at = str(user['joined_at'] or '').strip()
    if min_account_age > 0 and joined_at:
        try:
            joined_dt = datetime.strptime(joined_at, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - joined_dt < timedelta(days=min_account_age):
                conn.close(); return jsonify({'ok': False, 'error': f'Account must be at least {min_account_age} day(s) old'}), 400
        except Exception:
            pass

    row = _last_finished_game(cur, user_id)
    cooldown = int(cfg['mines_cooldown_seconds'])
    if row and cooldown > 0:
        try:
            last_dt = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
            remaining = cooldown - int((datetime.now() - last_dt).total_seconds())
            if remaining > 0:
                conn.close(); return jsonify({'ok': False, 'error': f'Cooldown active. Wait {remaining}s'}), 400
        except Exception:
            pass

    today_count = _count_today(cur, user_id)
    if today_count >= int(cfg['mines_daily_limit']):
        conn.close(); return jsonify({'ok': False, 'error': 'Daily play limit reached'}), 400
    last_hour_count = _count_last_hour(cur, user_id)
    if last_hour_count >= int(cfg['mines_hourly_limit']):
        conn.close(); return jsonify({'ok': False, 'error': 'Hourly play limit reached'}), 400

    bet_fee = round(bet * float(cfg['mines_bet_fee_percent']) / 100.0, 2)
    total_deduct = round(bet + bet_fee, 2)
    if _get_balance(user, balance_source) < total_deduct:
        conn.close(); return jsonify({'ok': False, 'error': 'Insufficient selected balance for bet + fee'}), 400

    game_id = uuid.uuid4().hex
    now = _now()
    force_mode = 'force_win' if bool(cfg['mines_force_win_global']) else 'force_loss' if bool(cfg['mines_force_loss_global']) else 'auto'
    _set_balance(cur, user_id, balance_source, _get_balance(user, balance_source) - total_deduct)
    cur.execute(
        "INSERT INTO mine_games (game_id, user_id, grid_rows, grid_cols, bet_amount, balance_source, mine_count, mine_positions, revealed_tiles, safe_picks, status, multiplier, gross_payout, net_payout, bet_fee, winning_tax, gst_amount, current_risk, seed_used, force_mode, auto_cashout_multiplier, forced_cashout_after, created_at, updated_at, meta_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            game_id, user_id, int(cfg['mines_grid_rows']), int(cfg['mines_grid_cols']), bet, balance_source, mine_count, json.dumps([]), json.dumps([]), 0,
            'active', 1.0, 0.0, 0.0, bet_fee, 0.0, 0.0, _risk_value(0, mine_count, total_tiles), '', force_mode,
            auto_cashout_multiplier if bool(cfg['mines_auto_cashout_enabled']) else 0.0,
            int(cfg['mines_force_cashout_after'] or 0), now, now,
            json.dumps({'house_edge': cfg['mines_house_edge'], 'grid_tiles': total_tiles})
        )
    )
    conn.commit()
    updated = _user_row(cur, user_id)
    conn.close()
    return jsonify({'ok': True, 'game_id': game_id, 'balances': _balances_dict(updated), 'balance_source': balance_source})


@app.route('/api/mine/reveal', methods=['POST'])
def api_mine_reveal():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get('uid') or data.get('user_id') or 0)
    game_id = str(data.get('game_id') or '').strip()
    tile = int(data.get('tile')) if data.get('tile') is not None else -1
    if user_id <= 0 or not game_id or tile < 0:
        return jsonify({'ok': False, 'error': 'Invalid request'}), 400
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    cur.execute("SELECT * FROM mine_games WHERE game_id=? AND user_id=?", (game_id, user_id))
    game = cur.fetchone()
    if not game:
        conn.close(); return jsonify({'ok': False, 'error': 'Game not found'}), 404
    if game['status'] != 'active':
        conn.close(); return jsonify({'ok': False, 'error': 'Game already finished'}), 400

    total_tiles = int(game['grid_rows']) * int(game['grid_cols'])
    if tile >= total_tiles:
        conn.close(); return jsonify({'ok': False, 'error': 'Invalid tile'}), 400
    cfg = _settings_blob(cur)
    force_mode = str(game['force_mode'] or 'auto')
    revealed = _json_load(game['revealed_tiles'], []) or []
    if tile in revealed:
        conn.close(); return jsonify({'ok': False, 'error': 'Tile already revealed'}), 400

    mine_positions = _json_load(game['mine_positions'], []) or []
    if not mine_positions:
        first_safe = tile if bool(cfg['mines_force_safe_first_tile']) else None
        mine_positions = _pick_mines(total_tiles, int(game['mine_count']), first_safe, force_mode)

    now = _now()
    is_mine = tile in set(mine_positions)
    cur.execute("INSERT INTO mine_tile_clicks (user_id, game_id, tile_index, was_mine, created_at) VALUES (?,?,?,?,?)", (user_id, game_id, tile, 1 if is_mine else 0, now))

    if is_mine and force_mode == 'force_win':
        is_mine = False

    if is_mine:
        meta = {'source': 'web', 'mines': sorted(mine_positions), 'revealed': revealed, 'game_id': game_id, 'balance_source': game['balance_source']}
        cur.execute("UPDATE mine_games SET mine_positions=?, status='lost', updated_at=?, ended_at=?, meta_json=? WHERE game_id=?", (json.dumps(mine_positions), now, now, json.dumps(meta), game_id))
        cur.execute("INSERT INTO game_history (user_id, game_key, bet_amount, reward_amount, outcome, round_meta, created_at) VALUES (?,?,?,?,?,?,?)", (user_id, 'mines', float(game['bet_amount'] or 0), 0.0, 'lose', json.dumps(meta), now))
        conn.commit()
        updated = _user_row(cur, user_id)
        conn.close()
        return jsonify({'ok': True, 'result': 'mine', 'balances': _balances_dict(updated), 'mines': sorted(mine_positions), 'game_over': True})

    revealed.append(tile)
    safe_picks = len(revealed)
    multiplier = _calc_multiplier(safe_picks, int(game['mine_count']), total_tiles, cfg)
    gross_payout = round(float(game['bet_amount'] or 0) * multiplier, 2)
    win_tax = round(max(0.0, gross_payout - float(game['bet_amount'] or 0)) * float(cfg['mines_winning_tax_percent']) / 100.0, 2)
    gst = round(max(0.0, gross_payout - float(game['bet_amount'] or 0)) * float(cfg['mines_gst_percent']) / 100.0, 2)
    net_payout = min(round(gross_payout - win_tax - gst, 2), float(cfg['mines_max_winnings_per_round']))
    current_risk = _risk_value(safe_picks, int(game['mine_count']), total_tiles)
    meta = {'grid_tiles': total_tiles, 'safe_picks': safe_picks, 'risk': current_risk}
    cur.execute("UPDATE mine_games SET mine_positions=?, revealed_tiles=?, safe_picks=?, multiplier=?, gross_payout=?, net_payout=?, winning_tax=?, gst_amount=?, current_risk=?, updated_at=?, meta_json=? WHERE game_id=?", (json.dumps(mine_positions), json.dumps(revealed), safe_picks, multiplier, gross_payout, net_payout, win_tax, gst, current_risk, now, json.dumps(meta), game_id))

    auto_cashout = float(game['auto_cashout_multiplier'] or 0)
    force_cashout_after = int(game['forced_cashout_after'] or 0)
    should_cashout = (auto_cashout > 0 and multiplier >= auto_cashout) or (force_cashout_after > 0 and safe_picks >= force_cashout_after)

    if should_cashout:
        user = _user_row(cur, user_id)
        today_win = _daily_winnings(cur, user_id)
        cap_left = max(0.0, float(cfg['mines_daily_win_cap']) - today_win)
        final_net = round(min(net_payout, cap_left), 2)
        _credit_win(cur, user, game['balance_source'], final_net)
        meta['auto_cashout'] = True
        cur.execute("UPDATE mine_games SET status='cashed_out', net_payout=?, updated_at=?, ended_at=?, meta_json=? WHERE game_id=?", (final_net, now, now, json.dumps(meta), game_id))
        cur.execute("INSERT INTO game_history (user_id, game_key, bet_amount, reward_amount, outcome, round_meta, created_at) VALUES (?,?,?,?,?,?,?)", (user_id, 'mines', float(game['bet_amount'] or 0), final_net, 'win', json.dumps(meta), now))
        conn.commit()
        updated = _user_row(cur, user_id)
        conn.close()
        return jsonify({'ok': True, 'result': 'gem', 'auto_cashed_out': True, 'multiplier': multiplier, 'payout': final_net, 'revealed_count': safe_picks, 'balances': _balances_dict(updated), 'game_over': True, 'mines': sorted(mine_positions)})

    conn.commit()
    updated = _user_row(cur, user_id)
    conn.close()
    return jsonify({'ok': True, 'result': 'gem', 'multiplier': multiplier, 'gross_payout': gross_payout, 'payout': net_payout, 'revealed_count': safe_picks, 'risk': current_risk, 'balances': _balances_dict(updated), 'game_over': False})


@app.route('/api/mine/cashout', methods=['POST'])
def api_mine_cashout():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get('uid') or data.get('user_id') or 0)
    game_id = str(data.get('game_id') or '').strip()
    if user_id <= 0 or not game_id:
        return jsonify({'ok': False, 'error': 'Invalid request'}), 400
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    cur.execute("SELECT * FROM mine_games WHERE game_id=? AND user_id=?", (game_id, user_id))
    game = cur.fetchone()
    if not game:
        conn.close(); return jsonify({'ok': False, 'error': 'Game not found'}), 404
    if game['status'] != 'active':
        conn.close(); return jsonify({'ok': False, 'error': 'Game already finished'}), 400
    if float(game['net_payout'] or 0) <= 0:
        conn.close(); return jsonify({'ok': False, 'error': 'Reveal at least one gem first'}), 400

    cfg = _settings_blob(cur)
    today_win = _daily_winnings(cur, user_id)
    cap_left = max(0.0, float(cfg['mines_daily_win_cap']) - today_win)
    payout = round(min(float(game['net_payout'] or 0), cap_left), 2)
    if payout <= 0:
        conn.close(); return jsonify({'ok': False, 'error': 'Daily win cap reached'}), 400
    user = _user_row(cur, user_id)
    _credit_win(cur, user, game['balance_source'], payout)
    now = _now()
    meta = _json_load(game['meta_json'], {}) or {}
    meta['manual_cashout'] = True
    cur.execute("UPDATE mine_games SET status='cashed_out', net_payout=?, updated_at=?, ended_at=?, meta_json=? WHERE game_id=?", (payout, now, now, json.dumps(meta), game_id))
    cur.execute("INSERT INTO game_history (user_id, game_key, bet_amount, reward_amount, outcome, round_meta, created_at) VALUES (?,?,?,?,?,?,?)", (user_id, 'mines', float(game['bet_amount'] or 0), payout, 'win', json.dumps(meta), now))
    conn.commit()
    updated = _user_row(cur, user_id)
    conn.close()
    return jsonify({'ok': True, 'payout': payout, 'balances': _balances_dict(updated)})


@app.route('/api/mine/history/<int:user_id>')
def api_mine_history(user_id):
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    cur.execute("SELECT game_key, bet_amount, reward_amount, outcome, round_meta, created_at FROM game_history WHERE user_id=? AND game_key='mines' ORDER BY id DESC LIMIT 30", (user_id,))
    rows = []
    for r in cur.fetchall():
        item = dict(r)
        item['round_meta'] = _json_load(item.get('round_meta'), {}) or {}
        rows.append(item)
    conn.close()
    return jsonify({'ok': True, 'items': rows})


@app.route('/api/mine/stats/<int:user_id>')
def api_mine_stats(user_id):
    conn = _db(); cur = conn.cursor(); _ensure_tables(cur)
    cur.execute("SELECT COUNT(*) games, COALESCE(SUM(bet_amount),0) total_bet, COALESCE(SUM(reward_amount),0) total_reward, COALESCE(AVG(reward_amount),0) avg_reward FROM game_history WHERE user_id=? AND game_key='mines'", (user_id,))
    user_stats = dict(cur.fetchone() or {})
    cur.execute("SELECT tile_index, COUNT(*) clicks FROM mine_tile_clicks GROUP BY tile_index ORDER BY clicks DESC LIMIT 12")
    heatmap = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT user_id, game_id, safe_picks, multiplier, gross_payout, balance_source, created_at FROM mine_games WHERE status='active' ORDER BY updated_at DESC LIMIT 20")
    active = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({'ok': True, 'user_stats': user_stats, 'heatmap': heatmap, 'active_sessions': active})


@app.errorhandler(404)
def not_found(e):
    return {'error': 'Not Found', 'message': 'Invalid route'}, 404


@app.errorhandler(500)
def server_error(e):
    logging.exception("Web server error: %s", e)
    return {'error': 'Server Error', 'message': 'Something went wrong'}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
