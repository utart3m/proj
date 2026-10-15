from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pathlib import Path
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'super_secret_key_for_sessions' 

# Вынесем подключение к БД в отдельную функцию для удобства
def get_db_connection():
    return mysql.connector.connect(
        host="185.114.247.43",
        port=3306,
        database="sch688_vvedenie",
        user="sch688_vvedenie",
        password="Qwerty123"
    )

@app.route('/user_register', methods=['POST'])
def user_register():
    req = request.get_json()
    name = req['name']
    email = req['email']
    password = req['password']
    hashed_password = generate_password_hash(password)
    
    try:
        cnx = get_db_connection()
        cur = cnx.cursor()
        cur.execute('INSERT INTO `users`(`username`, `email`, `password_hash`, `balance`) VALUES (%s, %s, %s, %s)', (name, email, hashed_password, 100))
        cnx.commit()
        user_id = cur.lastrowid
        cnx.close()

        session['user_id'] = user_id
        session['username'] = name
        session['balance'] = 100
        
        return jsonify({"result": True})
    except Exception as e:
        print("Ошибка регистрации:", e)
        return jsonify({"result": False})


@app.route('/user_login', methods=['POST'])
def user_login():
    req = request.get_json()
    uname = req['uname']
    password = req['p_hash']
    
    try:
        cnx = get_db_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute('SELECT * FROM users WHERE username=%s OR email=%s', (uname, uname))
        user = cur.fetchone()
        cnx.close()
        
        # Проверяем, существует ли пользователь и совпадает ли хеш пароля
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            save_login(user['id'])
            session['username'] = user['username']
            session['balance'] = user.get('balance', 0)
            return jsonify({"result": True})
        else:
            return jsonify({"result": False})
    except Exception as e:
        print("Ошибка входа:", e)
        return jsonify({"result": False})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
def registration():
    # Если уже авторизован — пускаем в ЛК
    if 'user_id' in session:
        return redirect(url_for('to_lk'))
    return render_template('registration.html')

@app.route("/login")
def login():
    if 'user_id' in session:
        return redirect(url_for('to_lk'))
    return render_template('login.html')

@app.route("/lk")
def to_lk():
    # Проверка, авторизован ли пользователь
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    udt = {
        'username': session.get('username'),
        'balance': session.get('balance'),
    }
    return render_template('lk.html', user=udt)


@app.route("/make_request", methods=['POST'])
def make_request():
    # Проверка авторизации
    if 'user_id' not in session:
        return jsonify({"result": False, "error": "Не авторизован"})
    
    current_balance = session.get('balance', 0)
    
    # Списание 3 рублей
    if current_balance >= 3:
        new_balance = current_balance - 3
        try:
            cnx = get_db_connection()
            cur = cnx.cursor()
            # Обновляем баланс в базе данных
            cur.execute('UPDATE users SET balance=%s WHERE id=%s', (new_balance, session['user_id']))
            cnx.commit()
            cnx.close()
            
            # Обновляем баланс в сессии
            session['balance'] = new_balance
            return jsonify({"result": True, "new_balance": new_balance})
        except Exception as e:
            return jsonify({"result": False, "error": "Ошибка базы данных"})
    else:
        return jsonify({"result": False, "error": "Недостаточно средств на балансе"})
HISTORY_DB = Path(__file__).with_name("login_history.sqlite3")
 
def history_connection():
    conn = sqlite3.connect(str(HISTORY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn
 
def save_login(user_id):
    conn = history_connection()
    try:
        time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        conn.execute(
            "INSERT INTO login_history (user_id, login_time) VALUES (?, ?)",
            (user_id, time)
        )
        conn.commit()
    finally:
        conn.close()
 
@app.route('/history')
def history():
    if 'user_id' not in session:
        return render_template('login.html')
 
    conn = history_connection()
    try:
        rows = conn.execute(
            """SELECT login_time FROM login_history
               WHERE user_id = ? ORDER BY id DESC""",
            (session['user_id'],)
        ).fetchall()
    finally:
        conn.close()
 
    return render_template('history.html', entries=rows)
if __name__ == '__main__':
    app.run(debug=True)