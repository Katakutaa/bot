import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "orders.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            direction TEXT,
            requirement_file_id TEXT,
            status TEXT DEFAULT 'pending',
            payment_screenshot_id TEXT,
            payment_date TIMESTAMP,
            completed_file_id TEXT,
            completed_date TIMESTAMP,
            admin_note TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(telegram_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (telegram_id, username, full_name, created_at)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, username or "", full_name or "", datetime.now()))
    conn.commit()
    conn.close()

def update_user_info(telegram_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE users SET username = ?, full_name = ? WHERE telegram_id = ?
    ''', (username or "", full_name or "", telegram_id))
    conn.commit()
    conn.close()

def create_order(telegram_id: int, direction: str, requirement_file_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (telegram_id, direction, requirement_file_id, created_at, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, direction, requirement_file_id, datetime.now(), 'pending'))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_payment(order_id: int, screenshot_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE orders
        SET payment_screenshot_id = ?, payment_date = ?, status = 'pending_payment'
        WHERE order_id = ?
    ''', (screenshot_id, datetime.now(), order_id))
    conn.commit()
    conn.close()

def update_order_status(order_id: int, status: str, admin_note: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if admin_note:
        c.execute('''
            UPDATE orders
            SET status = ?, admin_note = ?
            WHERE order_id = ?
        ''', (status, admin_note, order_id))
    else:
        c.execute('''
            UPDATE orders
            SET status = ?
            WHERE order_id = ?
        ''', (status, order_id))
    conn.commit()
    conn.close()

def update_order_completed(order_id: int, file_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE orders
        SET completed_file_id = ?, completed_date = ?, status = 'completed'
        WHERE order_id = ?
    ''', (file_id, datetime.now(), order_id))
    conn.commit()
    conn.close()

def get_pending_orders() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT * FROM orders
        WHERE status IN ('pending', 'pending_payment')
        ORDER BY created_at ASC
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_orders(telegram_id: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT * FROM orders
        WHERE telegram_id = ?
        ORDER BY created_at DESC
    ''', (telegram_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None